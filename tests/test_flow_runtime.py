from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

import support  # noqa: F401  # Adds the repository source root to sys.path.

from onlyiflow.runtime import Runtime


class FlowRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="OnlyiFlow flow runtime ")
        self.addCleanup(self.temporary.cleanup)
        self.project_root = Path(self.temporary.name) / "project with spaces"
        self.project_root.mkdir()
        self.runtime = Runtime()
        initialized = self.runtime.project_init(str(self.project_root))
        self.assertTrue(initialized["ok"])
        configured = self.runtime.gate_configure(
            str(self.project_root), [self.gate_check()]
        )
        self.assertTrue(configured["ok"])

    def test_quick_flow_starts_implementing_without_spec(self) -> None:
        result = self.runtime.flow_start(
            str(self.project_root),
            risk="quick",
            title="  Fix cache invalidation  ",
        )

        self.assertTrue(result["ok"])
        flow = result["data"]["flow"]
        self.assertEqual(flow["risk"], "quick")
        self.assertEqual(flow["title"], "Fix cache invalidation")
        self.assertEqual(flow["state"], "implementing")
        self.assertRegex(flow["id"], r"^[0-9a-f]{32}$")
        self.assertNotIn("next_action", result)
        self.assertEqual(list(self.specs_root.iterdir()), [])

        status = self.runtime.project_status(str(self.project_root))
        self.assertEqual(status["data"]["active_flow"], flow)
        self.assertEqual(
            status["next_action"],
            {"tool": "gate_run", "reason_code": "implementation_active"},
        )
        self.assert_events([(flow["id"], "flow_started", None, "implementing")])

    def test_standard_and_deep_flows_start_draft(self) -> None:
        for risk in ["standard", "deep"]:
            with self.subTest(risk=risk):
                project = self.new_managed_project(risk)
                result = self.runtime.flow_start(
                    str(project),
                    risk=risk,
                    title=f"{risk} change",
                )

                self.assertTrue(result["ok"])
                self.assertEqual(result["data"]["flow"]["state"], "draft")
                self.assertEqual(
                    result["next_action"],
                    {"tool": "spec_submit", "reason_code": "spec_required"},
                )

    def test_flow_start_rejects_unmanaged_invalid_risk_and_invalid_title(self) -> None:
        unmanaged = Path(self.temporary.name) / "unmanaged"
        unmanaged.mkdir()

        unmanaged_result = self.runtime.flow_start(
            str(unmanaged), risk="quick", title="Change"
        )
        invalid_risk = self.runtime.flow_start(
            str(self.project_root), risk="urgent", title="Change"
        )
        blank_title = self.runtime.flow_start(
            str(self.project_root), risk="quick", title="   "
        )
        long_title = self.runtime.flow_start(
            str(self.project_root), risk="quick", title="x" * 201
        )

        self.assert_error(unmanaged_result, "project_unmanaged")
        self.assertEqual(
            unmanaged_result["next_action"],
            {
                "tool": "project_init",
                "reason_code": "owner_confirmation_required",
            },
        )
        self.assert_error(invalid_risk, "risk_invalid")
        self.assert_error(blank_title, "title_required")
        self.assert_error(long_title, "title_too_long")
        self.assertFalse((unmanaged / ".onlyiflow").exists())

    def test_active_flow_conflict_is_structured(self) -> None:
        first = self.runtime.flow_start(
            str(self.project_root), risk="quick", title="First"
        )
        second = self.runtime.flow_start(
            str(self.project_root), risk="standard", title="Second"
        )

        self.assertTrue(first["ok"])
        self.assert_error(second, "active_flow_exists")
        self.assertTrue(second["error"]["retryable"])
        self.assertEqual(
            second["next_action"],
            {"tool": "project_status", "reason_code": "resume_active_flow"},
        )
        self.assertEqual(self.flow_count(), 1)

    def test_abandoned_accepts_every_nonterminal_state_and_releases_slot(self) -> None:
        for state in [
            "draft",
            "ready",
            "implementing",
            "gate_passed",
            "waiting_owner",
        ]:
            with self.subTest(state=state):
                project = self.new_managed_project(f"abandon-{state}")
                flow = self.runtime.flow_start(
                    str(project), risk="quick", title=f"Abandon {state}"
                )["data"]["flow"]
                database = project / ".onlyiflow/onlyiflow.db"
                with closing(sqlite3.connect(database)) as connection:
                    connection.execute(
                        "UPDATE flows SET state = ? WHERE id = ?", (state, flow["id"])
                    )
                    connection.commit()

                closed = self.runtime.flow_close(
                    str(project),
                    flow["id"],
                    action="abandoned",
                    reason_code="owner_cancelled",
                )

                self.assertTrue(closed["ok"], closed)
                self.assertEqual(
                    closed["data"],
                    {
                        "flow_id": flow["id"],
                        "previous_state": state,
                        "state": "abandoned",
                        "action": "abandoned",
                        "reason_code": "owner_cancelled",
                        "external_action_performed": False,
                    },
                )
                self.assertEqual(
                    closed["next_action"],
                    {"tool": "flow_start", "reason_code": "project_ready"},
                )
                replacement = self.runtime.flow_start(
                    str(project), risk="quick", title="Replacement"
                )
                self.assertTrue(replacement["ok"], replacement)
                with closing(sqlite3.connect(database)) as connection:
                    event = connection.execute(
                        """
                        SELECT from_state, to_state, reason_code
                        FROM domain_events
                        WHERE flow_id = ? AND event_type = 'flow_abandoned'
                        """,
                        (flow["id"],),
                    ).fetchone()
                self.assertEqual(event, (state, "abandoned", "owner_cancelled"))

    def test_landed_requires_waiting_owner_and_records_completed_landing(self) -> None:
        flow = self.runtime.flow_start(
            str(self.project_root), risk="quick", title="Owner landing"
        )["data"]["flow"]

        premature = self.runtime.flow_close(
            str(self.project_root),
            flow["id"],
            action="landed",
            reason_code="external_landing_completed",
        )
        self.assert_error(premature, "flow_close_not_allowed")
        self.assertEqual(self.flow_state(flow["id"]), "implementing")

        self.assertTrue(self.runtime.gate_run(str(self.project_root), flow["id"])["ok"])
        self.assertTrue(
            self.runtime.landing_request(str(self.project_root), flow["id"])["ok"]
        )
        closed = self.runtime.flow_close(
            str(self.project_root),
            flow["id"],
            action="landed",
            reason_code="external_landing_completed",
        )

        self.assertTrue(closed["ok"], closed)
        self.assertEqual(closed["data"]["previous_state"], "waiting_owner")
        self.assertEqual(closed["data"]["state"], "landed")
        self.assertFalse(closed["data"]["external_action_performed"])
        self.assertIsNone(
            self.runtime.project_status(str(self.project_root))["data"]["active_flow"]
        )
        with closing(sqlite3.connect(self.database)) as connection:
            reason = connection.execute(
                """
                SELECT reason_code FROM domain_events
                WHERE flow_id = ? AND event_type = 'flow_landed'
                """,
                (flow["id"],),
            ).fetchone()[0]
        self.assertEqual(reason, "external_landing_completed")

    def test_flow_close_rejects_unknown_actions_reasons_and_terminal_repeats(
        self,
    ) -> None:
        flow = self.runtime.flow_start(
            str(self.project_root), risk="quick", title="Validate close"
        )["data"]["flow"]

        invalid_action = self.runtime.flow_close(
            str(self.project_root), flow["id"], "closed", "owner_cancelled"
        )
        invalid_reason = self.runtime.flow_close(
            str(self.project_root), flow["id"], "abandoned", "free_form_reason"
        )
        mismatched_reason = self.runtime.flow_close(
            str(self.project_root),
            flow["id"],
            "abandoned",
            "external_landing_completed",
        )

        self.assert_error(invalid_action, "flow_close_action_invalid")
        self.assert_error(invalid_reason, "flow_close_reason_invalid")
        self.assert_error(mismatched_reason, "flow_close_reason_invalid")
        closed = self.runtime.flow_close(
            str(self.project_root), flow["id"], "abandoned", "goal_invalidated"
        )
        self.assertTrue(closed["ok"], closed)
        repeated = self.runtime.flow_close(
            str(self.project_root), flow["id"], "abandoned", "goal_superseded"
        )
        self.assert_error(repeated, "flow_close_not_allowed")

    def test_v2_flow_close_migrates_additively_and_preserves_existing_rows(
        self,
    ) -> None:
        project = self.new_managed_project("schema-v2-close")
        database = project / ".onlyiflow/onlyiflow.db"
        database.unlink()
        flow_id = "a" * 32
        with closing(sqlite3.connect(database)) as connection:
            connection.executescript(
                f"""
                CREATE TABLE flows (
                    id TEXT PRIMARY KEY,
                    risk TEXT NOT NULL,
                    title TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE specs (
                    flow_id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    acceptance TEXT NOT NULL,
                    boundaries TEXT NOT NULL,
                    expected_files_json TEXT NOT NULL,
                    submitted_at TEXT NOT NULL
                );
                CREATE TABLE gates (
                    id INTEGER PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    flow_id TEXT NOT NULL,
                    check_id TEXT NOT NULL,
                    required INTEGER NOT NULL,
                    passed INTEGER NOT NULL,
                    reason_code TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    exit_code INTEGER,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE domain_events (
                    id INTEGER PRIMARY KEY,
                    flow_id TEXT,
                    event_type TEXT NOT NULL,
                    from_state TEXT,
                    to_state TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE wave_plans (
                    flow_id TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                INSERT INTO flows VALUES (
                    '{flow_id}', 'quick', 'Existing v2 flow', 'implementing',
                    '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00'
                );
                INSERT INTO domain_events (
                    flow_id, event_type, from_state, to_state, created_at
                ) VALUES (
                    '{flow_id}', 'flow_started', NULL, 'implementing',
                    '2026-01-01T00:00:00+00:00'
                );
                PRAGMA user_version = 2;
                """
            )

        status = self.runtime.project_status(str(project))
        self.assertTrue(status["ok"], status)
        with closing(sqlite3.connect(database)) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 2)
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(domain_events)")
            }
        self.assertNotIn("reason_code", columns)

        closed = self.runtime.flow_close(
            str(project), flow_id, "abandoned", "scope_drifted"
        )

        self.assertTrue(closed["ok"], closed)
        with closing(sqlite3.connect(database)) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 3)
            events = connection.execute(
                """
                SELECT event_type, reason_code FROM domain_events
                WHERE flow_id = ? ORDER BY id
                """,
                (flow_id,),
            ).fetchall()
        self.assertEqual(
            events,
            [("flow_started", None), ("flow_abandoned", "scope_drifted")],
        )

    def test_legacy_empty_gate_close_returns_gate_configuration_next(self) -> None:
        project = Path(self.temporary.name) / "legacy-empty-gate-close"
        project.mkdir()
        self.assertTrue(self.runtime.project_init(str(project))["ok"])
        database = project / ".onlyiflow/onlyiflow.db"
        flow_id = "b" * 32
        with closing(sqlite3.connect(database)) as connection:
            connection.execute(
                """
                INSERT INTO flows (
                    id, risk, title, state, created_at, updated_at
                ) VALUES (?, 'quick', 'Legacy', 'implementing', ?, ?)
                """,
                (
                    flow_id,
                    "2026-01-01T00:00:00+00:00",
                    "2026-01-01T00:00:00+00:00",
                ),
            )
            connection.commit()

        closed = self.runtime.flow_close(
            str(project), flow_id, "abandoned", "goal_superseded"
        )

        self.assertTrue(closed["ok"], closed)
        self.assertEqual(
            closed["next_action"],
            {"tool": "gate_configure", "reason_code": "gate_configuration_required"},
        )

    def test_concurrent_flow_starts_create_exactly_one_active_flow(self) -> None:
        def start(index: int) -> dict:
            return Runtime().flow_start(
                str(self.project_root),
                risk="quick",
                title=f"Concurrent {index}",
            )

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(start, range(4)))

        self.assertEqual(sum(result["ok"] for result in results), 1)
        self.assertEqual(
            [result["error"]["code"] for result in results if not result["ok"]],
            ["active_flow_exists"] * 3,
        )
        self.assertEqual(self.flow_count(), 1)
        self.assertEqual(self.event_count("flow_started"), 1)

    def test_standard_spec_moves_flow_to_ready_and_writes_compact_artifact(
        self,
    ) -> None:
        flow = self.start_standard()

        result = self.runtime.spec_submit(
            str(self.project_root),
            flow_id=flow["id"],
            goal="  Add deterministic state  ",
            acceptance="  State survives a new process.  ",
            boundaries="  No agent configuration edits.  ",
            expected_files=["src/onlyiflow/runtime.py", "tests/test_flow_runtime.py"],
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["flow_id"], flow["id"])
        self.assertEqual(result["data"]["state"], "ready")
        self.assertEqual(
            result["data"]["spec"],
            {
                "goal": "Add deterministic state",
                "acceptance": "State survives a new process.",
                "boundaries": "No agent configuration edits.",
                "expected_files": [
                    "src/onlyiflow/runtime.py",
                    "tests/test_flow_runtime.py",
                ],
            },
        )
        self.assertEqual(
            result["next_action"],
            {"tool": "flow_claim", "reason_code": "flow_ready"},
        )

        artifact = self.specs_root / f"{flow['id']}.json"
        self.assertTrue(artifact.is_file())
        self.assertEqual(
            json.loads(artifact.read_text(encoding="utf-8")),
            {"flow_id": flow["id"], **result["data"]["spec"]},
        )
        self.assertNotIn(str(self.project_root), artifact.read_text(encoding="utf-8"))
        self.assertEqual(self.flow_state(flow["id"]), "ready")
        self.assert_events(
            [
                (flow["id"], "flow_started", None, "draft"),
                (flow["id"], "spec_submitted", "draft", "ready"),
            ]
        )

    def test_spec_validation_rejects_quick_missing_and_unsafe_files(self) -> None:
        quick = self.runtime.flow_start(
            str(self.project_root), risk="quick", title="Quick"
        )["data"]["flow"]
        quick_result = self.submit_spec(quick["id"])
        self.assert_error(quick_result, "spec_not_allowed")

        project = self.new_managed_project("missing")
        missing = self.runtime.spec_submit(
            str(project),
            flow_id="0" * 32,
            goal="Goal",
            acceptance="Acceptance",
            boundaries="Boundaries",
            expected_files=["src/app.py"],
        )
        self.assert_error(missing, "flow_not_found")

        for expected_files in [
            [],
            ["../outside.py"],
            ["C:/outside.py"],
            ["src/app.py", "SRC/app.py"],
            [""],
        ]:
            project = self.new_managed_project(
                f"invalid-{len(expected_files)}-{abs(hash(tuple(expected_files)))}"
            )
            flow = self.runtime.flow_start(
                str(project), risk="standard", title="Standard"
            )["data"]["flow"]
            result = self.runtime.spec_submit(
                str(project),
                flow_id=flow["id"],
                goal="Goal",
                acceptance="Acceptance",
                boundaries="Boundaries",
                expected_files=expected_files,
            )
            self.assert_error(result, "expected_files_invalid")

    def test_spec_validation_rejects_blank_and_oversized_text(self) -> None:
        cases = [
            ("goal", "   ", "goal_required"),
            ("goal", "x" * 4001, "goal_too_long"),
            ("acceptance", "   ", "acceptance_required"),
            ("boundaries", "x" * 4001, "boundaries_too_long"),
        ]
        for index, (field, value, code) in enumerate(cases):
            with self.subTest(field=field, code=code):
                project = self.new_managed_project(f"invalid-text-{index}")
                flow = self.runtime.flow_start(
                    str(project), risk="standard", title="Standard"
                )["data"]["flow"]
                arguments = {
                    "project_root": str(project),
                    "flow_id": flow["id"],
                    "goal": "Goal",
                    "acceptance": "Acceptance",
                    "boundaries": "Boundaries",
                    "expected_files": ["src/app.py"],
                }
                arguments[field] = value

                result = self.runtime.spec_submit(**arguments)

                self.assert_error(result, code)

    def test_flow_claim_requires_ready_flow(self) -> None:
        flow = self.start_standard()
        premature = self.runtime.flow_claim(str(self.project_root), flow["id"])
        self.assert_error(premature, "invalid_transition")

        self.assertTrue(self.submit_spec(flow["id"])["ok"])
        claimed = self.runtime.flow_claim(str(self.project_root), flow["id"])

        self.assertTrue(claimed["ok"])
        self.assertEqual(claimed["data"]["flow"]["state"], "implementing")
        self.assertNotIn("next_action", claimed)
        self.assertEqual(self.flow_state(flow["id"]), "implementing")
        self.assert_events(
            [
                (flow["id"], "flow_started", None, "draft"),
                (flow["id"], "spec_submitted", "draft", "ready"),
                (flow["id"], "flow_claimed", "ready", "implementing"),
            ]
        )

    def test_flow_claim_rejects_invalid_and_missing_ids(self) -> None:
        invalid = self.runtime.flow_claim(str(self.project_root), "../bad")
        missing = self.runtime.flow_claim(str(self.project_root), "f" * 32)

        self.assert_error(invalid, "flow_id_invalid")
        self.assert_error(missing, "flow_not_found")

    def start_standard(self) -> dict:
        return self.runtime.flow_start(
            str(self.project_root),
            risk="standard",
            title="Standard change",
        )["data"]["flow"]

    def submit_spec(self, flow_id: str) -> dict:
        return self.runtime.spec_submit(
            str(self.project_root),
            flow_id=flow_id,
            goal="Goal",
            acceptance="Acceptance",
            boundaries="Boundaries",
            expected_files=["src/app.py"],
        )

    def new_managed_project(self, name: str) -> Path:
        project = Path(self.temporary.name) / name
        project.mkdir()
        self.assertTrue(self.runtime.project_init(str(project))["ok"])
        self.assertTrue(
            self.runtime.gate_configure(str(project), [self.gate_check()])["ok"]
        )
        return project

    def gate_check(self) -> dict:
        return {
            "id": "tests",
            "required": True,
            "command": ["python", "-c", "pass"],
            "timeout_seconds": 10,
        }

    @property
    def database(self) -> Path:
        return self.project_root / ".onlyiflow/onlyiflow.db"

    @property
    def specs_root(self) -> Path:
        return self.project_root / ".onlyiflow/specs"

    def flow_count(self) -> int:
        with closing(sqlite3.connect(self.database)) as connection:
            return connection.execute("SELECT COUNT(*) FROM flows").fetchone()[0]

    def flow_state(self, flow_id: str) -> str:
        with closing(sqlite3.connect(self.database)) as connection:
            return connection.execute(
                "SELECT state FROM flows WHERE id = ?", (flow_id,)
            ).fetchone()[0]

    def event_count(self, event_type: str) -> int:
        with closing(sqlite3.connect(self.database)) as connection:
            return connection.execute(
                "SELECT COUNT(*) FROM domain_events WHERE event_type = ?",
                (event_type,),
            ).fetchone()[0]

    def assert_events(
        self, expected: list[tuple[str, str, str | None, str | None]]
    ) -> None:
        with closing(sqlite3.connect(self.database)) as connection:
            events = connection.execute(
                """
                SELECT flow_id, event_type, from_state, to_state
                FROM domain_events
                ORDER BY id
                """
            ).fetchall()
        self.assertEqual(events, expected)

    def assert_error(self, result: dict, code: str) -> None:
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], code)


if __name__ == "__main__":
    unittest.main()
