"""Persist workflow state, migrations, and compact evidence in project-local SQLite."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from .contracts import DomainError
from .paths import ProjectPaths
from .waves import changed_files_in_scope, contract_equal


DEFAULT_CONFIG = """version = 1
checks = []
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS flows (
    id TEXT PRIMARY KEY,
    risk TEXT NOT NULL CHECK (risk IN ('quick', 'standard', 'deep')),
    title TEXT NOT NULL,
    state TEXT NOT NULL CHECK (
        state IN (
            'draft',
            'ready',
            'implementing',
            'gate_passed',
            'waiting_owner',
            'landed',
            'abandoned'
        )
    ),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS one_non_terminal_flow
ON flows ((1))
WHERE state IN ('draft', 'ready', 'implementing', 'gate_passed', 'waiting_owner');

CREATE TABLE IF NOT EXISTS specs (
    flow_id TEXT PRIMARY KEY REFERENCES flows(id) ON DELETE CASCADE,
    goal TEXT NOT NULL,
    acceptance TEXT NOT NULL,
    boundaries TEXT NOT NULL,
    expected_files_json TEXT NOT NULL,
    submitted_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gates (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    flow_id TEXT NOT NULL REFERENCES flows(id) ON DELETE CASCADE,
    check_id TEXT NOT NULL,
    required INTEGER NOT NULL CHECK (required IN (0, 1)),
    passed INTEGER NOT NULL CHECK (passed IN (0, 1)),
    reason_code TEXT NOT NULL,
    duration_ms INTEGER NOT NULL,
    exit_code INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS domain_events (
    id INTEGER PRIMARY KEY,
    flow_id TEXT REFERENCES flows(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    from_state TEXT,
    to_state TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS wave_plans (
    flow_id TEXT PRIMARY KEY REFERENCES flows(id) ON DELETE CASCADE,
    revision INTEGER NOT NULL CHECK (revision >= 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS work_packages (
    flow_id TEXT NOT NULL REFERENCES flows(id) ON DELETE CASCADE,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    package_id TEXT NOT NULL,
    wave_index INTEGER NOT NULL CHECK (wave_index >= 0),
    contract_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'proposed',
            'ready',
            'running',
            'submitted',
            'changes_requested',
            'accepted',
            'integrated',
            'blocked',
            'deferred',
            'superseded'
        )
    ),
    attempt_count INTEGER NOT NULL CHECK (attempt_count >= 0),
    base_commit TEXT,
    head_commit TEXT,
    changed_files_json TEXT NOT NULL,
    checks_json TEXT NOT NULL,
    known_limits_json TEXT NOT NULL,
    reason_code TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (flow_id, revision, package_id)
);

CREATE TABLE IF NOT EXISTS package_dependencies (
    flow_id TEXT NOT NULL REFERENCES flows(id) ON DELETE CASCADE,
    revision INTEGER NOT NULL,
    package_id TEXT NOT NULL,
    dependency_id TEXT NOT NULL,
    PRIMARY KEY (flow_id, revision, package_id, dependency_id),
    FOREIGN KEY (flow_id, revision, package_id)
        REFERENCES work_packages(flow_id, revision, package_id) ON DELETE CASCADE,
    FOREIGN KEY (flow_id, revision, dependency_id)
        REFERENCES work_packages(flow_id, revision, package_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS package_events (
    id INTEGER PRIMARY KEY,
    flow_id TEXT NOT NULL REFERENCES flows(id) ON DELETE CASCADE,
    revision INTEGER NOT NULL,
    package_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    from_state TEXT,
    to_state TEXT,
    attempt INTEGER NOT NULL CHECK (attempt >= 0),
    reason_code TEXT,
    created_at TEXT NOT NULL
);

PRAGMA user_version = 2;
"""


class ProjectStore:
    def __init__(self, paths: ProjectPaths):
        self.paths = paths

    def initialize(self) -> bool:
        created = not self.paths.is_managed()
        self.paths.state_root.mkdir(exist_ok=True)
        self.paths.specs.mkdir(exist_ok=True)
        if not self.paths.config.exists():
            self.paths.config.write_text(DEFAULT_CONFIG, encoding="utf-8")

        self.ensure_schema()
        return created

    def ensure_schema(self) -> None:
        with self.connection() as connection:
            connection.executescript(SCHEMA)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.paths.database, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @contextmanager
    def transaction(self, *, immediate: bool = False) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            # Immediate transactions serialize competing workflow-state mutations.
            connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def active_flow(self) -> dict | None:
        with self.connection() as connection:
            if self._schema_version(connection) < 2:
                row = connection.execute(
                    """
                    SELECT
                        id,
                        risk,
                        title,
                        state,
                        created_at,
                        updated_at,
                        'direct' AS mode
                    FROM flows
                    WHERE state IN (
                        'draft', 'ready', 'implementing', 'gate_passed', 'waiting_owner'
                    )
                    LIMIT 1
                    """
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT
                        flows.id,
                        flows.risk,
                        flows.title,
                        flows.state,
                        flows.created_at,
                        flows.updated_at,
                        CASE WHEN wave_plans.flow_id IS NULL THEN 'direct' ELSE 'wave' END AS mode
                    FROM flows
                    LEFT JOIN wave_plans ON wave_plans.flow_id = flows.id
                    WHERE flows.state IN (
                        'draft', 'ready', 'implementing', 'gate_passed', 'waiting_owner'
                    )
                    LIMIT 1
                    """
                ).fetchone()
        return dict(row) if row is not None else None

    def latest_gate(self) -> dict | None:
        with self.connection() as connection:
            latest = connection.execute(
                """
                SELECT run_id, flow_id
                FROM gates
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            if latest is None:
                return None
            rows = connection.execute(
                """
                SELECT check_id, required, passed, reason_code, duration_ms, exit_code
                FROM gates
                WHERE run_id = ?
                ORDER BY id
                """,
                (latest["run_id"],),
            ).fetchall()
        checks = [
            {
                "check_id": row["check_id"],
                "required": bool(row["required"]),
                "passed": bool(row["passed"]),
                "reason_code": row["reason_code"],
                "duration_ms": row["duration_ms"],
                "exit_code": row["exit_code"],
            }
            for row in rows
        ]
        return {
            "flow_id": latest["flow_id"],
            "passed": all(check["passed"] for check in checks if check["required"]),
            "checks": checks,
        }

    def create_flow(self, flow: dict, *, mode: str = "direct") -> dict:
        with self.transaction(immediate=True) as connection:
            active = self._active_flow(connection)
            if active is not None:
                raise DomainError(
                    code="active_flow_exists",
                    message="A non-terminal flow already exists.",
                    retryable=True,
                    next_action={
                        "tool": "project_status",
                        "reason_code": "resume_active_flow",
                    },
                )
            connection.execute(
                """
                INSERT INTO flows (id, risk, title, state, created_at, updated_at)
                VALUES (:id, :risk, :title, :state, :created_at, :updated_at)
                """,
                flow,
            )
            if mode == "wave":
                connection.execute(
                    """
                    INSERT INTO wave_plans (flow_id, revision, created_at, updated_at)
                    VALUES (?, 0, ?, ?)
                    """,
                    (flow["id"], flow["created_at"], flow["created_at"]),
                )
            self._append_event(
                connection,
                flow_id=flow["id"],
                event_type="flow_started",
                from_state=None,
                to_state=flow["state"],
                created_at=flow["created_at"],
            )
        return {**flow, "mode": mode}

    def get_flow(self, flow_id: str) -> dict:
        with self.connection() as connection:
            row = self._flow(connection, flow_id)
        if row is None:
            raise self.flow_not_found()
        return dict(row)

    def submit_spec(
        self,
        *,
        flow_id: str,
        spec: dict,
        submitted_at: str,
    ) -> dict:
        artifact = self.paths.specs / f"{flow_id}.json"
        wrote_artifact = False
        try:
            with self.transaction(immediate=True) as connection:
                row = self._flow(connection, flow_id)
                if row is None:
                    raise self.flow_not_found()
                if row["risk"] == "quick":
                    raise DomainError(
                        code="spec_not_allowed",
                        message="Quick flows do not use a spec.",
                        retryable=False,
                    )
                if row["state"] != "draft":
                    raise self.invalid_transition(row["state"], "ready")

                artifact.write_text(
                    json_text({"flow_id": flow_id, **spec}),
                    encoding="utf-8",
                )
                wrote_artifact = True
                connection.execute(
                    """
                    INSERT INTO specs (
                        flow_id, goal, acceptance, boundaries,
                        expected_files_json, submitted_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        flow_id,
                        spec["goal"],
                        spec["acceptance"],
                        spec["boundaries"],
                        json_text(spec["expected_files"], compact=True),
                        submitted_at,
                    ),
                )
                connection.execute(
                    "UPDATE flows SET state = 'ready', updated_at = ? WHERE id = ?",
                    (submitted_at, flow_id),
                )
                self._append_event(
                    connection,
                    flow_id=flow_id,
                    event_type="spec_submitted",
                    from_state="draft",
                    to_state="ready",
                    created_at=submitted_at,
                )
                updated = self._flow(connection, flow_id)
            return dict(updated)
        except Exception:
            if wrote_artifact:
                artifact.unlink(missing_ok=True)
            raise

    def claim_flow(self, *, flow_id: str, claimed_at: str) -> dict:
        with self.transaction(immediate=True) as connection:
            row = self._flow(connection, flow_id)
            if row is None:
                raise self.flow_not_found()
            if row["state"] != "ready":
                raise self.invalid_transition(row["state"], "implementing")
            connection.execute(
                "UPDATE flows SET state = 'implementing', updated_at = ? WHERE id = ?",
                (claimed_at, flow_id),
            )
            self._append_event(
                connection,
                flow_id=flow_id,
                event_type="flow_claimed",
                from_state="ready",
                to_state="implementing",
                created_at=claimed_at,
            )
            updated = self._flow(connection, flow_id)
        return dict(updated)

    def require_gate_runnable(self, flow_id: str) -> dict:
        flow = self.get_flow(flow_id)
        if flow["state"] != "implementing":
            raise self.invalid_transition(flow["state"], "gate_passed")
        return flow

    def record_gate(
        self,
        *,
        flow_id: str,
        run_id: str,
        checks: list[dict],
        passed: bool,
        recorded_at: str,
    ) -> dict:
        with self.transaction(immediate=True) as connection:
            row = self._flow(connection, flow_id)
            if row is None:
                raise self.flow_not_found()
            if row["state"] != "implementing":
                raise self.invalid_transition(row["state"], "gate_passed")

            for check in checks:
                connection.execute(
                    """
                    INSERT INTO gates (
                        run_id, flow_id, check_id, required, passed,
                        reason_code, duration_ms, exit_code, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        flow_id,
                        check["check_id"],
                        int(check["required"]),
                        int(check["passed"]),
                        check["reason_code"],
                        check["duration_ms"],
                        check["exit_code"],
                        recorded_at,
                    ),
                )
            state = "gate_passed" if passed else "implementing"
            connection.execute(
                "UPDATE flows SET state = ?, updated_at = ? WHERE id = ?",
                (state, recorded_at, flow_id),
            )
            self._append_event(
                connection,
                flow_id=flow_id,
                event_type="gate_passed" if passed else "gate_failed",
                from_state="implementing",
                to_state=state,
                created_at=recorded_at,
            )
            updated = self._flow(connection, flow_id)
        return dict(updated)

    def request_landing(self, *, flow_id: str, requested_at: str) -> dict:
        with self.transaction(immediate=True) as connection:
            row = self._flow(connection, flow_id)
            if row is None:
                raise self.flow_not_found()
            if row["state"] != "gate_passed":
                raise self.invalid_transition(row["state"], "waiting_owner")
            connection.execute(
                "UPDATE flows SET state = 'waiting_owner', updated_at = ? WHERE id = ?",
                (requested_at, flow_id),
            )
            self._append_event(
                connection,
                flow_id=flow_id,
                event_type="landing_requested",
                from_state="gate_passed",
                to_state="waiting_owner",
                created_at=requested_at,
            )
            updated = self._flow(connection, flow_id)
        return dict(updated)

    def wave_plan_summary(self, flow_id: str) -> dict | None:
        with self.connection() as connection:
            if self._schema_version(connection) < 2:
                return None
            return self._wave_summary(connection, flow_id)

    def _schema_version(self, connection: sqlite3.Connection) -> int:
        return int(connection.execute("PRAGMA user_version").fetchone()[0])

    def set_wave_plan(
        self,
        *,
        flow_id: str,
        expected_revision: int,
        packages: list[dict],
        recorded_at: str,
    ) -> dict:
        with self.transaction(immediate=True) as connection:
            flow = self._flow(connection, flow_id)
            if flow is None:
                raise self.flow_not_found()
            if flow["mode"] != "wave" or flow["risk"] != "deep":
                raise DomainError(
                    code="wave_plan_not_allowed",
                    message="Only deep Wave flows accept a Wave plan.",
                    retryable=False,
                )
            plan = connection.execute(
                "SELECT revision FROM wave_plans WHERE flow_id = ?",
                (flow_id,),
            ).fetchone()
            current_revision = plan["revision"]
            if expected_revision != current_revision:
                raise DomainError(
                    code="wave_plan_revision_conflict",
                    message="Wave plan revision does not match current state.",
                    retryable=True,
                    next_action={
                        "tool": "project_status",
                        "reason_code": "refresh_project_state",
                    },
                )
            if current_revision == 0 and flow["state"] != "ready":
                raise self.invalid_transition(flow["state"], "ready")
            if current_revision > 0 and flow["state"] != "implementing":
                raise self.invalid_transition(flow["state"], "implementing")

            current_rows = self._package_rows(connection, flow_id, current_revision)
            transient = {
                "running",
                "submitted",
                "changes_requested",
                "accepted",
            }
            if any(row["status"] in transient for row in current_rows):
                raise DomainError(
                    code="wave_plan_revision_busy",
                    message="Pause active package work before revising the Wave plan.",
                    retryable=True,
                    next_action={
                        "tool": "work_package_status",
                        "reason_code": "resolve_active_packages",
                    },
                )

            by_id = {package["id"]: package for package in packages}
            current_by_id = {row["package_id"]: row for row in current_rows}
            for row in current_rows:
                if row["status"] != "integrated":
                    continue
                replacement = by_id.get(row["package_id"])
                if replacement is None or not contract_equal(
                    json.loads(row["contract_json"]), replacement
                ):
                    raise DomainError(
                        code="integrated_package_immutable",
                        message="Integrated package contracts cannot change during replan.",
                        retryable=True,
                        next_action={
                            "tool": "wave_plan_set",
                            "reason_code": "preserve_integrated_packages",
                        },
                    )

            for row in current_rows:
                if row["status"] == "integrated":
                    continue
                connection.execute(
                    """
                    UPDATE work_packages SET status = 'superseded', updated_at = ?
                    WHERE flow_id = ? AND revision = ? AND package_id = ?
                    """,
                    (recorded_at, flow_id, current_revision, row["package_id"]),
                )
                self._append_package_event(
                    connection,
                    flow_id=flow_id,
                    revision=current_revision,
                    package_id=row["package_id"],
                    event_type="package_superseded",
                    from_state=row["status"],
                    to_state="superseded",
                    attempt=row["attempt_count"],
                    reason_code=None,
                    created_at=recorded_at,
                )

            revision = current_revision + 1
            empty_json = json_text([], compact=True)
            for package in packages:
                previous = current_by_id.get(package["id"])
                integrated = previous is not None and previous["status"] == "integrated"
                connection.execute(
                    """
                    INSERT INTO work_packages (
                        flow_id, revision, package_id, wave_index, contract_json,
                        status, attempt_count, base_commit, head_commit,
                        changed_files_json, checks_json, known_limits_json,
                        reason_code, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        flow_id,
                        revision,
                        package["id"],
                        package["wave"],
                        json_text(package, compact=True),
                        "integrated" if integrated else "proposed",
                        previous["attempt_count"] if previous is not None else 0,
                        previous["base_commit"] if integrated else None,
                        previous["head_commit"] if integrated else None,
                        previous["changed_files_json"] if integrated else empty_json,
                        previous["checks_json"] if integrated else empty_json,
                        previous["known_limits_json"] if integrated else empty_json,
                        previous["reason_code"] if integrated else None,
                        recorded_at,
                        recorded_at,
                    ),
                )
            for package in packages:
                for dependency in package["dependencies"]:
                    connection.execute(
                        """
                        INSERT INTO package_dependencies (
                            flow_id, revision, package_id, dependency_id
                        )
                        VALUES (?, ?, ?, ?)
                        """,
                        (flow_id, revision, package["id"], dependency),
                    )
            connection.execute(
                """
                UPDATE wave_plans SET revision = ?, updated_at = ? WHERE flow_id = ?
                """,
                (revision, recorded_at, flow_id),
            )
            self._refresh_ready(connection, flow_id, revision, recorded_at)
            self._append_event(
                connection,
                flow_id=flow_id,
                event_type="wave_plan_set" if revision == 1 else "wave_plan_revised",
                from_state=flow["state"],
                to_state=flow["state"],
                created_at=recorded_at,
            )
            return self._wave_summary(connection, flow_id)

    def work_package(self, flow_id: str, package_id: str) -> dict:
        with self.connection() as connection:
            if self._schema_version(connection) < 2:
                raise self.package_not_found()
            row = self._current_package(connection, flow_id, package_id)
            if row is None:
                raise self.package_not_found()
            return self._package_data(row)

    def record_package(
        self,
        *,
        flow_id: str,
        package_id: str,
        record: dict,
        recorded_at: str,
    ) -> tuple[dict, dict]:
        with self.transaction(immediate=True) as connection:
            flow = self._flow(connection, flow_id)
            if flow is None:
                raise self.flow_not_found()
            if flow["mode"] != "wave" or flow["state"] != "implementing":
                raise DomainError(
                    code="package_record_not_allowed",
                    message="Package records require an implementing Wave flow.",
                    retryable=True,
                    next_action={
                        "tool": "project_status",
                        "reason_code": "refresh_project_state",
                    },
                )
            row = self._current_package(connection, flow_id, package_id)
            if row is None:
                raise self.package_not_found()

            # Records attest to completed host work; this layer never executes that work.
            action = record["action"]
            current = row["status"]
            target = current
            attempt = row["attempt_count"]
            values: dict[str, object] = {
                "base_commit": row["base_commit"],
                "head_commit": row["head_commit"],
                "changed_files_json": row["changed_files_json"],
                "checks_json": row["checks_json"],
                "known_limits_json": row["known_limits_json"],
                "reason_code": row["reason_code"],
            }

            if action == "start":
                if current == "ready":
                    attempt += 1
                elif current != "changes_requested":
                    raise self.package_transition_error(current, action)
                target = "running"
                values["reason_code"] = None
            elif action == "submit":
                if current != "running":
                    raise self.package_transition_error(current, action)
                contract = json.loads(row["contract_json"])
                if not changed_files_in_scope(record["changed_files"], contract):
                    raise DomainError(
                        code="package_changed_files_out_of_scope",
                        message="Declared changed files exceed the package path contract.",
                        retryable=True,
                        next_action={
                            "tool": "work_package_status",
                            "reason_code": "refresh_package_state",
                        },
                    )
                if {check["check_id"] for check in record["checks"]} != set(
                    contract["check_ids"]
                ):
                    raise DomainError(
                        code="package_checks_mismatch",
                        message="Package checks must match the confirmed package contract.",
                        retryable=True,
                        next_action={
                            "tool": "work_package_status",
                            "reason_code": "refresh_package_state",
                        },
                    )
                target = "submitted"
                values.update(
                    {
                        "base_commit": record["base_commit"],
                        "head_commit": record["head_commit"],
                        "changed_files_json": json_text(
                            record["changed_files"], compact=True
                        ),
                        "checks_json": json_text(record["checks"], compact=True),
                        "known_limits_json": json_text(
                            record["known_limits"], compact=True
                        ),
                        "reason_code": None,
                    }
                )
            elif action == "request_changes":
                if current != "submitted":
                    raise self.package_transition_error(current, action)
                target = "changes_requested"
                values["reason_code"] = record["reason_code"]
            elif action == "accept":
                if current != "submitted":
                    raise self.package_transition_error(current, action)
                if not all(check["passed"] for check in json.loads(row["checks_json"])):
                    raise DomainError(
                        code="package_checks_failed",
                        message="A package with failed confirmed checks cannot be accepted.",
                        retryable=True,
                        next_action={
                            "tool": "work_package_status",
                            "reason_code": "package_changes_required",
                        },
                    )
                target = "accepted"
                values["reason_code"] = None
            elif action == "integrate":
                if current != "accepted":
                    raise self.package_transition_error(current, action)
                if row["head_commit"] != record["head_commit"]:
                    raise DomainError(
                        code="package_commit_mismatch",
                        message="Integrated commit must match the submitted head commit.",
                        retryable=True,
                        next_action={
                            "tool": "work_package_status",
                            "reason_code": "refresh_package_state",
                        },
                    )
                target = "integrated"
                values["reason_code"] = None
            elif action == "interrupt":
                if current != "running":
                    raise self.package_transition_error(current, action)
                contract = json.loads(row["contract_json"])
                if "changed_files" in record and not changed_files_in_scope(
                    record["changed_files"], contract
                ):
                    raise DomainError(
                        code="package_changed_files_out_of_scope",
                        message="Declared changed files exceed the package path contract.",
                        retryable=True,
                        next_action={
                            "tool": "work_package_status",
                            "reason_code": "refresh_package_state",
                        },
                    )
                target = "ready" if record["retryable"] else "blocked"
                values["reason_code"] = record["reason_code"]
                if "base_commit" in record:
                    values["base_commit"] = record["base_commit"]
                if "head_commit" in record:
                    values["head_commit"] = record["head_commit"]
                if "changed_files" in record:
                    values["changed_files_json"] = json_text(
                        record["changed_files"], compact=True
                    )
            elif action == "block":
                if current not in {"proposed", "ready", "running"}:
                    raise self.package_transition_error(current, action)
                target = "blocked"
                values["reason_code"] = record["reason_code"]
            elif action == "resume":
                if current != "blocked" or not self._package_can_be_ready(
                    connection, flow_id, row["revision"], package_id
                ):
                    raise self.package_transition_error(current, action)
                target = "ready"
                values["reason_code"] = record["reason_code"]
            elif action == "defer":
                contract = json.loads(row["contract_json"])
                if (
                    current not in {"proposed", "ready", "blocked"}
                    or contract["condition"] is None
                ):
                    raise self.package_transition_error(current, action)
                target = "deferred"
                values["reason_code"] = record["reason_code"]
            else:  # pragma: no cover - normalize_record rejects unknown actions.
                raise self.package_transition_error(current, action)

            connection.execute(
                """
                UPDATE work_packages
                SET status = ?, attempt_count = ?, base_commit = ?, head_commit = ?,
                    changed_files_json = ?, checks_json = ?, known_limits_json = ?,
                    reason_code = ?, updated_at = ?
                WHERE flow_id = ? AND revision = ? AND package_id = ?
                """,
                (
                    target,
                    attempt,
                    values["base_commit"],
                    values["head_commit"],
                    values["changed_files_json"],
                    values["checks_json"],
                    values["known_limits_json"],
                    values["reason_code"],
                    recorded_at,
                    flow_id,
                    row["revision"],
                    package_id,
                ),
            )
            self._append_package_event(
                connection,
                flow_id=flow_id,
                revision=row["revision"],
                package_id=package_id,
                event_type=f"package_{action}",
                from_state=current,
                to_state=target,
                attempt=attempt,
                reason_code=values["reason_code"],
                created_at=recorded_at,
            )
            if target in {"integrated", "deferred"}:
                self._refresh_ready(connection, flow_id, row["revision"], recorded_at)
            updated = self._current_package(connection, flow_id, package_id)
            return self._package_data(updated), self._wave_summary(connection, flow_id)

    def wave_plan_complete(self, flow_id: str) -> bool:
        summary = self.wave_plan_summary(flow_id)
        return bool(
            summary is not None
            and summary["configured"]
            and summary["current_wave"] is None
        )

    def _wave_summary(
        self, connection: sqlite3.Connection, flow_id: str
    ) -> dict | None:
        plan = connection.execute(
            "SELECT revision FROM wave_plans WHERE flow_id = ?",
            (flow_id,),
        ).fetchone()
        if plan is None:
            return None
        revision = plan["revision"]
        rows = self._package_rows(connection, flow_id, revision)
        status_counts: dict[str, int] = {}
        for row in rows:
            status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
        unfinished = [
            row for row in rows if row["status"] not in {"integrated", "deferred"}
        ]
        current_wave = min((row["wave_index"] for row in unfinished), default=None)
        ready = sorted(
            row["package_id"]
            for row in rows
            if row["status"] == "ready" and row["wave_index"] == current_wave
        )
        attention_statuses = {
            "running",
            "submitted",
            "changes_requested",
            "accepted",
            "blocked",
        }
        attention = [
            {
                "package_id": row["package_id"],
                "status": row["status"],
                "attempt_count": row["attempt_count"],
            }
            for row in rows
            if row["status"] in attention_statuses
            and (current_wave is None or row["wave_index"] == current_wave)
        ]
        attention.sort(key=lambda item: item["package_id"])
        return {
            "flow_id": flow_id,
            "configured": revision > 0,
            "revision": revision,
            "package_count": len(rows),
            "current_wave": current_wave,
            "ready_packages": ready,
            "attention_packages": attention,
            "status_counts": status_counts,
        }

    def _package_rows(
        self, connection: sqlite3.Connection, flow_id: str, revision: int
    ) -> list[sqlite3.Row]:
        if revision == 0:
            return []
        return connection.execute(
            """
            SELECT * FROM work_packages
            WHERE flow_id = ? AND revision = ?
            ORDER BY wave_index, package_id
            """,
            (flow_id, revision),
        ).fetchall()

    def _current_package(
        self,
        connection: sqlite3.Connection,
        flow_id: str,
        package_id: str,
    ) -> sqlite3.Row | None:
        return connection.execute(
            """
            SELECT work_packages.*
            FROM work_packages
            JOIN wave_plans
              ON wave_plans.flow_id = work_packages.flow_id
             AND wave_plans.revision = work_packages.revision
            WHERE work_packages.flow_id = ? AND work_packages.package_id = ?
            """,
            (flow_id, package_id),
        ).fetchone()

    def _package_data(self, row: sqlite3.Row) -> dict:
        contract = json.loads(row["contract_json"])
        return {
            **contract,
            "revision": row["revision"],
            "status": row["status"],
            "attempt_count": row["attempt_count"],
            "base_commit": row["base_commit"],
            "head_commit": row["head_commit"],
            "changed_files": json.loads(row["changed_files_json"]),
            "checks": json.loads(row["checks_json"]),
            "known_limits": json.loads(row["known_limits_json"]),
            "reason_code": row["reason_code"],
        }

    def _refresh_ready(
        self,
        connection: sqlite3.Connection,
        flow_id: str,
        revision: int,
        recorded_at: str,
    ) -> None:
        rows = self._package_rows(connection, flow_id, revision)
        for row in rows:
            if row["status"] != "proposed" or not self._package_can_be_ready(
                connection, flow_id, revision, row["package_id"]
            ):
                continue
            connection.execute(
                """
                UPDATE work_packages SET status = 'ready', updated_at = ?
                WHERE flow_id = ? AND revision = ? AND package_id = ?
                """,
                (recorded_at, flow_id, revision, row["package_id"]),
            )
            self._append_package_event(
                connection,
                flow_id=flow_id,
                revision=revision,
                package_id=row["package_id"],
                event_type="package_ready",
                from_state="proposed",
                to_state="ready",
                attempt=row["attempt_count"],
                reason_code=None,
                created_at=recorded_at,
            )

    def _package_can_be_ready(
        self,
        connection: sqlite3.Connection,
        flow_id: str,
        revision: int,
        package_id: str,
    ) -> bool:
        row = connection.execute(
            """
            SELECT wave_index FROM work_packages
            WHERE flow_id = ? AND revision = ? AND package_id = ?
            """,
            (flow_id, revision, package_id),
        ).fetchone()
        if row is None:
            return False
        # Readiness requires both prior Waves and explicit dependencies to be complete.
        lower_incomplete = connection.execute(
            """
            SELECT 1 FROM work_packages
            WHERE flow_id = ? AND revision = ? AND wave_index < ?
              AND status NOT IN ('integrated', 'deferred')
            LIMIT 1
            """,
            (flow_id, revision, row["wave_index"]),
        ).fetchone()
        if lower_incomplete is not None:
            return False
        dependency_incomplete = connection.execute(
            """
            SELECT 1
            FROM package_dependencies
            JOIN work_packages dependency
              ON dependency.flow_id = package_dependencies.flow_id
             AND dependency.revision = package_dependencies.revision
             AND dependency.package_id = package_dependencies.dependency_id
            WHERE package_dependencies.flow_id = ?
              AND package_dependencies.revision = ?
              AND package_dependencies.package_id = ?
              AND dependency.status != 'integrated'
            LIMIT 1
            """,
            (flow_id, revision, package_id),
        ).fetchone()
        return dependency_incomplete is None

    def _append_package_event(
        self,
        connection: sqlite3.Connection,
        *,
        flow_id: str,
        revision: int,
        package_id: str,
        event_type: str,
        from_state: str | None,
        to_state: str | None,
        attempt: int,
        reason_code: str | None,
        created_at: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO package_events (
                flow_id, revision, package_id, event_type, from_state,
                to_state, attempt, reason_code, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                flow_id,
                revision,
                package_id,
                event_type,
                from_state,
                to_state,
                attempt,
                reason_code,
                created_at,
            ),
        )

    def package_not_found(self) -> DomainError:
        return DomainError(
            code="package_not_found",
            message="Work package does not exist in the current Wave plan.",
            retryable=True,
            next_action={
                "tool": "project_status",
                "reason_code": "refresh_project_state",
            },
        )

    def package_transition_error(self, current: str, action: str) -> DomainError:
        return DomainError(
            code="package_transition_invalid",
            message=f"Work package cannot record {action} from {current}.",
            retryable=True,
            next_action={
                "tool": "work_package_status",
                "reason_code": "refresh_package_state",
            },
        )

    def _active_flow(self, connection: sqlite3.Connection) -> sqlite3.Row | None:
        return connection.execute(
            """
            SELECT
                flows.id,
                flows.risk,
                flows.title,
                flows.state,
                flows.created_at,
                flows.updated_at,
                CASE WHEN wave_plans.flow_id IS NULL THEN 'direct' ELSE 'wave' END AS mode
            FROM flows
            LEFT JOIN wave_plans ON wave_plans.flow_id = flows.id
            WHERE flows.state IN (
                'draft', 'ready', 'implementing', 'gate_passed', 'waiting_owner'
            )
            LIMIT 1
            """
        ).fetchone()

    def _flow(self, connection: sqlite3.Connection, flow_id: str) -> sqlite3.Row | None:
        return connection.execute(
            """
            SELECT
                flows.id,
                flows.risk,
                flows.title,
                flows.state,
                flows.created_at,
                flows.updated_at,
                CASE WHEN wave_plans.flow_id IS NULL THEN 'direct' ELSE 'wave' END AS mode
            FROM flows
            LEFT JOIN wave_plans ON wave_plans.flow_id = flows.id
            WHERE flows.id = ?
            """,
            (flow_id,),
        ).fetchone()

    def _append_event(
        self,
        connection: sqlite3.Connection,
        *,
        flow_id: str,
        event_type: str,
        from_state: str | None,
        to_state: str | None,
        created_at: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO domain_events (
                flow_id, event_type, from_state, to_state, created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (flow_id, event_type, from_state, to_state, created_at),
        )

    def flow_not_found(self) -> DomainError:
        return DomainError(
            code="flow_not_found",
            message="Flow does not exist.",
            retryable=True,
            next_action={
                "tool": "project_status",
                "reason_code": "refresh_project_state",
            },
        )

    def invalid_transition(self, current: str, target: str) -> DomainError:
        return DomainError(
            code="invalid_transition",
            message=f"Flow cannot move from {current} to {target}.",
            retryable=True,
            next_action={
                "tool": "project_status",
                "reason_code": "refresh_project_state",
            },
        )


def json_text(value: object, *, compact: bool = False) -> str:
    import json

    if compact:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
