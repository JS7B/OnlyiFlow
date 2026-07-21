"""协调项目、Flow、Wave、Gate 与落地操作。"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable

from .contracts import DomainError, Payload, failure, success
from .domain import (
    MAX_SPEC_TEXT_LENGTH,
    MAX_TITLE_LENGTH,
    new_flow_id,
    utc_now,
    validate_flow_id,
    validate_risk,
    validate_text,
)
from .gates import (
    configure_gate_checks,
    gate_config_summary,
    load_gate_checks,
    run_gate_checks,
)
from .paths import (
    INITIALIZATION_ENTRIES,
    normalize_expected_files,
    resolve_project_root,
)
from .storage import ProjectStore
from .waves import (
    normalize_packages,
    normalize_record,
    validate_flow_mode,
    validate_package_id,
)


class Runtime:
    def project_status(self, project_root: str) -> Payload:
        return self._execute(lambda: self._project_status(project_root))

    def project_init(self, project_root: str) -> Payload:
        return self._execute(lambda: self._project_init(project_root))

    def gate_configure(self, project_root: str, checks: list[dict]) -> Payload:
        return self._execute(lambda: self._gate_configure(project_root, checks))

    def flow_start(
        self,
        project_root: str,
        risk: str,
        title: str,
        mode: str = "direct",
    ) -> Payload:
        return self._execute(lambda: self._flow_start(project_root, risk, title, mode))

    def spec_submit(
        self,
        project_root: str,
        flow_id: str,
        goal: str,
        acceptance: str,
        boundaries: str,
        expected_files: list[str],
    ) -> Payload:
        return self._execute(
            lambda: self._spec_submit(
                project_root,
                flow_id,
                goal,
                acceptance,
                boundaries,
                expected_files,
            )
        )

    def flow_claim(self, project_root: str, flow_id: str) -> Payload:
        return self._execute(lambda: self._flow_claim(project_root, flow_id))

    def wave_plan_set(
        self,
        project_root: str,
        flow_id: str,
        expected_revision: int,
        packages: list[dict],
    ) -> Payload:
        return self._execute(
            lambda: self._wave_plan_set(
                project_root,
                flow_id,
                expected_revision,
                packages,
            )
        )

    def work_package_status(
        self,
        project_root: str,
        flow_id: str,
        package_id: str,
    ) -> Payload:
        return self._execute(
            lambda: self._work_package_status(project_root, flow_id, package_id)
        )

    def work_package_record(
        self,
        project_root: str,
        flow_id: str,
        package_id: str,
        action: str,
        base_commit: str | None = None,
        head_commit: str | None = None,
        changed_files: list[str] | None = None,
        checks: list[dict] | None = None,
        known_limits: list[str] | None = None,
        reason_code: str | None = None,
        retryable: bool | None = None,
    ) -> Payload:
        return self._execute(
            lambda: self._work_package_record(
                project_root=project_root,
                flow_id=flow_id,
                package_id=package_id,
                action=action,
                base_commit=base_commit,
                head_commit=head_commit,
                changed_files=changed_files,
                checks=checks,
                known_limits=known_limits,
                reason_code=reason_code,
                retryable=retryable,
            )
        )

    def gate_run(self, project_root: str, flow_id: str) -> Payload:
        return self._execute(lambda: self._gate_run(project_root, flow_id))

    def landing_request(self, project_root: str, flow_id: str) -> Payload:
        return self._execute(lambda: self._landing_request(project_root, flow_id))

    def _project_status(self, project_root: str) -> Payload:
        paths = resolve_project_root(project_root)
        if not paths.is_managed():
            return success(
                {
                    "managed": False,
                    "initialization_entries": INITIALIZATION_ENTRIES,
                },
                {
                    "tool": "project_init",
                    "reason_code": "owner_confirmation_required",
                },
            )

        # 状态查询为只读操作，不得改动旧版 schema-version 1 项目。
        store = ProjectStore(paths)
        active_flow = store.active_flow()
        gate_config = gate_config_summary(store.paths.config)
        wave_plan = (
            store.wave_plan_summary(active_flow["id"])
            if active_flow is not None
            else None
        )
        return success(
            {
                "managed": True,
                "active_flow": active_flow,
                "latest_gate": store.latest_gate(),
                "gate_config": gate_config,
                "wave_plan": wave_plan,
            },
            self._status_next_action(active_flow, gate_config, wave_plan),
        )

    def _project_init(self, project_root: str) -> Payload:
        paths = resolve_project_root(project_root)
        created = ProjectStore(paths).initialize()
        return success(
            {
                "created": created,
                "entries": INITIALIZATION_ENTRIES,
            },
            {
                "tool": "gate_configure",
                "reason_code": "gate_configuration_required",
            },
        )

    def _gate_configure(self, project_root: str, raw_checks: list[dict]) -> Payload:
        store = self._managed_store(project_root)
        active_flow = store.active_flow()
        gate_config = gate_config_summary(store.paths.config)
        # 旧版空 Gate 可配置一次；活动流程中已配置的 Gate 保持冻结。
        if active_flow is not None and gate_config["configured"]:
            raise DomainError(
                code="gate_config_locked",
                message="Gate configuration cannot change while a flow is active.",
                retryable=True,
                next_action={
                    "tool": "project_status",
                    "reason_code": "resume_active_flow",
                },
            )
        checks = configure_gate_checks(store.paths.config, raw_checks)
        return success(
            {
                "checks": [
                    {
                        "check_id": check.check_id,
                        "required": check.required,
                        "timeout_seconds": check.timeout_seconds,
                    }
                    for check in checks
                ],
                "check_count": len(checks),
                "required_count": sum(check.required for check in checks),
            },
            self._status_next_action(
                active_flow,
                {
                    "configured": True,
                    "check_count": len(checks),
                    "required_count": sum(check.required for check in checks),
                },
                (
                    store.wave_plan_summary(active_flow["id"])
                    if active_flow is not None
                    else None
                ),
            ),
        )

    def _flow_start(
        self,
        project_root: str,
        risk: str,
        title: str,
        mode: str,
    ) -> Payload:
        store = self._managed_store(project_root)
        if not gate_config_summary(store.paths.config)["configured"]:
            raise DomainError(
                code="gate_checks_missing",
                message="No gate checks are configured.",
                retryable=True,
                next_action={
                    "tool": "gate_configure",
                    "reason_code": "gate_configuration_required",
                },
            )
        normalized_risk = validate_risk(risk)
        normalized_mode = validate_flow_mode(mode)
        if normalized_mode == "wave" and normalized_risk != "deep":
            raise DomainError(
                code="wave_mode_requires_deep",
                message="Wave mode requires deep risk.",
                retryable=True,
            )
        normalized_title = validate_text(
            title,
            field="title",
            maximum=MAX_TITLE_LENGTH,
        )
        timestamp = utc_now()
        state = "implementing" if normalized_risk == "quick" else "draft"
        flow = store.create_flow(
            {
                "id": new_flow_id(),
                "risk": normalized_risk,
                "title": normalized_title,
                "state": state,
                "created_at": timestamp,
                "updated_at": timestamp,
            },
            mode=normalized_mode,
        )
        next_action = None
        if state == "draft":
            next_action = {
                "tool": "spec_submit",
                "reason_code": "spec_required",
            }
        return success({"flow": flow}, next_action)

    def _spec_submit(
        self,
        project_root: str,
        flow_id: str,
        goal: str,
        acceptance: str,
        boundaries: str,
        expected_files: list[str],
    ) -> Payload:
        store = self._managed_store(project_root)
        normalized_flow_id = validate_flow_id(flow_id)
        spec = {
            "goal": validate_text(
                goal,
                field="goal",
                maximum=MAX_SPEC_TEXT_LENGTH,
            ),
            "acceptance": validate_text(
                acceptance,
                field="acceptance",
                maximum=MAX_SPEC_TEXT_LENGTH,
            ),
            "boundaries": validate_text(
                boundaries,
                field="boundaries",
                maximum=MAX_SPEC_TEXT_LENGTH,
            ),
            "expected_files": normalize_expected_files(expected_files),
        }
        flow = store.submit_spec(
            flow_id=normalized_flow_id,
            spec=spec,
            submitted_at=utc_now(),
        )
        next_action = (
            {"tool": "wave_plan_set", "reason_code": "wave_plan_required"}
            if flow["mode"] == "wave"
            else {"tool": "flow_claim", "reason_code": "flow_ready"}
        )
        return success(
            {
                "flow_id": normalized_flow_id,
                "state": "ready",
                "spec": spec,
            },
            next_action,
        )

    def _flow_claim(self, project_root: str, flow_id: str) -> Payload:
        store = self._managed_store(project_root)
        normalized_flow_id = validate_flow_id(flow_id)
        flow = store.get_flow(normalized_flow_id)
        wave_plan = store.wave_plan_summary(normalized_flow_id)
        if flow["mode"] == "wave" and (
            wave_plan is None or not wave_plan["configured"]
        ):
            raise DomainError(
                code="wave_plan_required",
                message="A confirmed Wave plan is required before claim.",
                retryable=True,
                next_action={
                    "tool": "wave_plan_set",
                    "reason_code": "wave_plan_required",
                },
            )
        flow = store.claim_flow(
            flow_id=normalized_flow_id,
            claimed_at=utc_now(),
        )
        return success(
            {"flow": flow},
            (
                self._wave_next_action(store.wave_plan_summary(normalized_flow_id))
                if flow["mode"] == "wave"
                else None
            ),
        )

    def _wave_plan_set(
        self,
        project_root: str,
        flow_id: str,
        expected_revision: int,
        packages: list[dict],
    ) -> Payload:
        store = self._managed_store(project_root)
        normalized_flow_id = validate_flow_id(flow_id)
        if (
            not isinstance(expected_revision, int)
            or isinstance(expected_revision, bool)
            or expected_revision < 0
        ):
            raise DomainError(
                code="wave_plan_revision_invalid",
                message="Expected Wave plan revision must be a non-negative integer.",
                retryable=True,
            )
        summary = store.set_wave_plan(
            flow_id=normalized_flow_id,
            expected_revision=expected_revision,
            packages=normalize_packages(packages),
            recorded_at=utc_now(),
        )
        flow = store.get_flow(normalized_flow_id)
        next_action = (
            {"tool": "flow_claim", "reason_code": "flow_ready"}
            if flow["state"] == "ready"
            else self._wave_next_action(summary)
        )
        return success(summary, next_action)

    def _work_package_status(
        self,
        project_root: str,
        flow_id: str,
        package_id: str,
    ) -> Payload:
        # 工作包查询属于只读路径，因此不得触发数据库模式迁移。
        store = self._managed_store(project_root, migrate=False)
        normalized_flow_id = validate_flow_id(flow_id)
        package = store.work_package(
            normalized_flow_id,
            validate_package_id(package_id),
        )
        return success(
            {"flow_id": normalized_flow_id, "package": package},
            self._package_next_action(package),
        )

    def _work_package_record(
        self,
        *,
        project_root: str,
        flow_id: str,
        package_id: str,
        action: str,
        base_commit: str | None,
        head_commit: str | None,
        changed_files: list[str] | None,
        checks: list[dict] | None,
        known_limits: list[str] | None,
        reason_code: str | None,
        retryable: bool | None,
    ) -> Payload:
        store = self._managed_store(project_root)
        normalized_flow_id = validate_flow_id(flow_id)
        package, summary = store.record_package(
            flow_id=normalized_flow_id,
            package_id=validate_package_id(package_id),
            record=normalize_record(
                action=action,
                base_commit=base_commit,
                head_commit=head_commit,
                changed_files=changed_files,
                checks=checks,
                known_limits=known_limits,
                reason_code=reason_code,
                retryable=retryable,
            ),
            recorded_at=utc_now(),
        )
        next_action = self._package_next_action(package)
        if package["status"] in {"integrated", "deferred"}:
            next_action = self._wave_next_action(summary)
        return success(
            {
                "flow_id": normalized_flow_id,
                "package": package,
                "wave_plan": summary,
            },
            next_action,
        )

    def _gate_run(self, project_root: str, flow_id: str) -> Payload:
        store = self._managed_store(project_root)
        normalized_flow_id = validate_flow_id(flow_id)
        flow = store.require_gate_runnable(normalized_flow_id)
        # 项目级 Gate 不能替代尚未完成的工作包交接。
        if flow["mode"] == "wave" and not store.wave_plan_complete(normalized_flow_id):
            raise DomainError(
                code="wave_packages_incomplete",
                message="All current Wave packages must be integrated or deferred first.",
                retryable=True,
                next_action=self._wave_next_action(
                    store.wave_plan_summary(normalized_flow_id)
                ),
            )
        checks = load_gate_checks(store.paths.config)
        evidence = run_gate_checks(checks, store.paths.root)
        passed = all(check["passed"] for check in evidence if check["required"])
        state = "gate_passed" if passed else "implementing"
        store.record_gate(
            flow_id=normalized_flow_id,
            run_id=new_flow_id(),
            checks=evidence,
            passed=passed,
            recorded_at=utc_now(),
        )
        next_action = (
            {"tool": "landing_request", "reason_code": "gates_passed"}
            if passed
            else {"tool": "gate_run", "reason_code": "required_check_failed"}
        )
        return success(
            {
                "flow_id": normalized_flow_id,
                "state": state,
                "passed": passed,
                "checks": evidence,
            },
            next_action,
        )

    def _landing_request(self, project_root: str, flow_id: str) -> Payload:
        store = self._managed_store(project_root)
        normalized_flow_id = validate_flow_id(flow_id)
        flow = store.request_landing(
            flow_id=normalized_flow_id,
            requested_at=utc_now(),
        )
        return success(
            {
                "flow_id": normalized_flow_id,
                "state": flow["state"],
                "direct_git_enforcement": False,
            }
        )

    def _managed_store(
        self, project_root: str, *, migrate: bool = True
    ) -> ProjectStore:
        paths = resolve_project_root(project_root)
        if not paths.is_managed():
            raise DomainError(
                code="project_unmanaged",
                message="Project is not initialized for OnlyiFlow.",
                retryable=True,
                next_action={
                    "tool": "project_init",
                    "reason_code": "owner_confirmation_required",
                },
            )
        store = ProjectStore(paths)
        # 写操作执行增量迁移；严格只读调用方可以明确禁用迁移。
        if migrate:
            store.ensure_schema()
        return store

    def _status_next_action(
        self,
        flow: dict | None,
        gate_config: dict,
        wave_plan: dict | None,
    ) -> dict[str, str] | None:
        if not gate_config["configured"]:
            return {
                "tool": "gate_configure",
                "reason_code": "gate_configuration_required",
            }
        if flow is None:
            return {"tool": "flow_start", "reason_code": "project_ready"}
        if flow["mode"] == "wave":
            if flow["state"] == "draft":
                return {"tool": "spec_submit", "reason_code": "spec_required"}
            if flow["state"] == "ready":
                if wave_plan is None or not wave_plan["configured"]:
                    return {
                        "tool": "wave_plan_set",
                        "reason_code": "wave_plan_required",
                    }
                return {"tool": "flow_claim", "reason_code": "flow_ready"}
            if flow["state"] == "implementing":
                return self._wave_next_action(wave_plan)
            if flow["state"] == "gate_passed":
                return {
                    "tool": "landing_request",
                    "reason_code": "gates_passed",
                }
            return None
        return {
            "draft": {"tool": "spec_submit", "reason_code": "spec_required"},
            "ready": {"tool": "flow_claim", "reason_code": "flow_ready"},
            "implementing": {
                "tool": "gate_run",
                "reason_code": "implementation_active",
            },
            "gate_passed": {
                "tool": "landing_request",
                "reason_code": "gates_passed",
            },
            "waiting_owner": None,
        }[flow["state"]]

    def _wave_next_action(self, summary: dict | None) -> dict[str, str] | None:
        if summary is None or not summary["configured"]:
            return {"tool": "wave_plan_set", "reason_code": "wave_plan_required"}
        attention = summary["attention_packages"]
        if attention:
            statuses = {package["status"] for package in attention}
            if "blocked" in statuses:
                return {"tool": "wave_plan_set", "reason_code": "package_blocked"}
            if "submitted" in statuses:
                return {
                    "tool": "work_package_status",
                    "reason_code": "package_review_required",
                }
            if "changes_requested" in statuses:
                return {
                    "tool": "work_package_status",
                    "reason_code": "package_changes_required",
                }
            if "accepted" in statuses:
                return {
                    "tool": "work_package_record",
                    "reason_code": "package_integration_record_required",
                }
            return {
                "tool": "work_package_status",
                "reason_code": "resume_active_package",
            }
        if summary["ready_packages"]:
            return {
                "tool": "work_package_status",
                "reason_code": "execute_current_wave",
            }
        if summary["current_wave"] is None:
            return {"tool": "gate_run", "reason_code": "implementation_complete"}
        return {"tool": "wave_plan_set", "reason_code": "replan_required"}

    def _package_next_action(self, package: dict) -> dict[str, str] | None:
        return {
            "proposed": {"tool": "project_status", "reason_code": "dependency_pending"},
            "ready": {
                "tool": "work_package_record",
                "reason_code": "package_ready",
            },
            "running": None,
            "submitted": {
                "tool": "work_package_record",
                "reason_code": "package_review_required",
            },
            "changes_requested": {
                "tool": "work_package_record",
                "reason_code": "package_changes_required",
            },
            "accepted": {
                "tool": "work_package_record",
                "reason_code": "package_integration_record_required",
            },
            "integrated": None,
            "blocked": {"tool": "wave_plan_set", "reason_code": "package_blocked"},
            "deferred": None,
        }[package["status"]]

    def _execute(self, operation: Callable[[], Payload]) -> Payload:
        try:
            return operation()
        except DomainError as error:
            return failure(error)
        # 不跨越 MCP 边界暴露宿主路径或数据库细节。
        except (OSError, sqlite3.Error):
            return failure(
                DomainError(
                    code="runtime_error",
                    message="OnlyiFlow could not update project state.",
                    retryable=False,
                )
            )
