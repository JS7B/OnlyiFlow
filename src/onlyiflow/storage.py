from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from .contracts import DomainError
from .paths import ProjectPaths


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

PRAGMA user_version = 1;
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

        with self.connection() as connection:
            connection.executescript(SCHEMA)
        return created

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
            row = connection.execute(
                """
                SELECT id, risk, title, state, created_at, updated_at
                FROM flows
                WHERE state IN (
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
            "passed": all(
                check["passed"] for check in checks if check["required"]
            ),
            "checks": checks,
        }

    def create_flow(self, flow: dict) -> dict:
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
            self._append_event(
                connection,
                flow_id=flow["id"],
                event_type="flow_started",
                from_state=None,
                to_state=flow["state"],
                created_at=flow["created_at"],
            )
        return flow

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

    def _active_flow(self, connection: sqlite3.Connection) -> sqlite3.Row | None:
        return connection.execute(
            """
            SELECT id, risk, title, state, created_at, updated_at
            FROM flows
            WHERE state IN (
                'draft', 'ready', 'implementing', 'gate_passed', 'waiting_owner'
            )
            LIMIT 1
            """
        ).fetchone()

    def _flow(
        self, connection: sqlite3.Connection, flow_id: str
    ) -> sqlite3.Row | None:
        return connection.execute(
            """
            SELECT id, risk, title, state, created_at, updated_at
            FROM flows
            WHERE id = ?
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
