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
from .gates import load_gate_checks, run_gate_checks
from .paths import (
    INITIALIZATION_ENTRIES,
    normalize_expected_files,
    resolve_project_root,
)
from .storage import ProjectStore


class Runtime:
    def project_status(self, project_root: str) -> Payload:
        return self._execute(lambda: self._project_status(project_root))

    def project_init(self, project_root: str) -> Payload:
        return self._execute(lambda: self._project_init(project_root))

    def flow_start(self, project_root: str, risk: str, title: str) -> Payload:
        return self._execute(lambda: self._flow_start(project_root, risk, title))

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

        store = ProjectStore(paths)
        active_flow = store.active_flow()
        return success(
            {
                "managed": True,
                "active_flow": active_flow,
                "latest_gate": store.latest_gate(),
            },
            self._status_next_action(active_flow),
        )

    def _project_init(self, project_root: str) -> Payload:
        paths = resolve_project_root(project_root)
        created = ProjectStore(paths).initialize()
        return success(
            {
                "created": created,
                "entries": INITIALIZATION_ENTRIES,
            },
            {"tool": "flow_start", "reason_code": "project_ready"},
        )

    def _flow_start(self, project_root: str, risk: str, title: str) -> Payload:
        store = self._managed_store(project_root)
        normalized_risk = validate_risk(risk)
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
            }
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
        store.submit_spec(
            flow_id=normalized_flow_id,
            spec=spec,
            submitted_at=utc_now(),
        )
        return success(
            {
                "flow_id": normalized_flow_id,
                "state": "ready",
                "spec": spec,
            },
            {"tool": "flow_claim", "reason_code": "flow_ready"},
        )

    def _flow_claim(self, project_root: str, flow_id: str) -> Payload:
        store = self._managed_store(project_root)
        flow = store.claim_flow(
            flow_id=validate_flow_id(flow_id),
            claimed_at=utc_now(),
        )
        return success({"flow": flow})

    def _gate_run(self, project_root: str, flow_id: str) -> Payload:
        store = self._managed_store(project_root)
        normalized_flow_id = validate_flow_id(flow_id)
        store.require_gate_runnable(normalized_flow_id)
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

    def _managed_store(self, project_root: str) -> ProjectStore:
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
        return ProjectStore(paths)

    def _status_next_action(self, flow: dict | None) -> dict[str, str] | None:
        if flow is None:
            return {"tool": "flow_start", "reason_code": "project_ready"}
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

    def _execute(self, operation: Callable[[], Payload]) -> Payload:
        try:
            return operation()
        except DomainError as error:
            return failure(error)
        except (OSError, sqlite3.Error):
            return failure(
                DomainError(
                    code="runtime_error",
                    message="OnlyiFlow could not update project state.",
                    retryable=False,
                )
            )
