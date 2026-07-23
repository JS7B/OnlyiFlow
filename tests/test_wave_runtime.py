from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

import support  # noqa: F401  # Adds the repository source root to sys.path.

from onlyiflow.runtime import Runtime


class WaveRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="OnlyiFlow wave runtime ")
        self.addCleanup(self.temporary.cleanup)
        self.project_root = Path(self.temporary.name) / "project with spaces"
        self.project_root.mkdir()
        self.runtime = Runtime()
        self.assertTrue(self.runtime.project_init(str(self.project_root))["ok"])
        self.assertTrue(
            self.runtime.gate_configure(
                str(self.project_root),
                [
                    {
                        "id": "tests",
                        "required": True,
                        "command": ["python", "-c", "pass"],
                        "timeout_seconds": 10,
                    }
                ],
            )["ok"]
        )

    def test_standard_wave_is_supported_and_quick_wave_is_rejected(self) -> None:
        invalid = self.runtime.flow_start(
            str(self.project_root),
            risk="quick",
            title="Invalid wave",
            mode="wave",
        )
        self.assert_error(invalid, "wave_mode_requires_standard_or_deep")

        flow = self.start_wave(risk="standard")
        self.assertEqual(flow["mode"], "wave")

        status = self.runtime.project_status(str(self.project_root))
        self.assertEqual(
            status["data"]["wave_plan"],
            {
                "flow_id": flow["id"],
                "configured": False,
                "revision": 0,
                "package_count": 0,
                "current_wave": None,
                "ready_packages": [],
                "attention_packages": [],
                "status_counts": {},
            },
        )
        self.assertEqual(
            status["next_action"],
            {"tool": "spec_submit", "reason_code": "spec_required"},
        )

        submitted = self.submit_spec(flow["id"])
        self.assertTrue(submitted["ok"])
        self.assertEqual(
            submitted["next_action"],
            {"tool": "wave_plan_set", "reason_code": "wave_plan_required"},
        )
        premature = self.runtime.flow_claim(str(self.project_root), flow["id"])
        self.assert_error(premature, "wave_plan_required")
        planned = self.runtime.wave_plan_set(
            str(self.project_root), flow["id"], 0, self.plan()
        )
        self.assertTrue(planned["ok"], planned)
        claimed = self.runtime.flow_claim(str(self.project_root), flow["id"])
        self.assertTrue(claimed["ok"], claimed)

    def test_landed_wave_close_preserves_spec_gate_plan_packages_and_events(
        self,
    ) -> None:
        flow = self.start_implementing_wave()
        for package_id, changed_file in {
            "P": "src/contracts.py",
            "Q": "src/backend.py",
            "R": "src/frontend.ts",
        }.items():
            self.complete_package(flow["id"], package_id, changed_file)
        gated = self.runtime.gate_run(str(self.project_root), flow["id"])
        self.assertTrue(gated["ok"], gated)
        self.assertTrue(
            self.runtime.landing_request(str(self.project_root), flow["id"])["ok"]
        )
        database = self.project_root / ".onlyiflow/onlyiflow.db"
        with closing(sqlite3.connect(database)) as connection:
            before = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in [
                    "flows",
                    "specs",
                    "gates",
                    "wave_plans",
                    "work_packages",
                    "package_dependencies",
                    "package_events",
                ]
            }
            event_count = connection.execute(
                "SELECT COUNT(*) FROM domain_events"
            ).fetchone()[0]

        closed = self.runtime.flow_close(
            str(self.project_root),
            flow["id"],
            "landed",
            "external_landing_completed",
        )

        self.assertTrue(closed["ok"], closed)
        with closing(sqlite3.connect(database)) as connection:
            after = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in before
            }
            events = connection.execute(
                """
                SELECT event_type, from_state, to_state, reason_code
                FROM domain_events ORDER BY id
                """
            ).fetchall()
        self.assertEqual(after, before)
        self.assertEqual(len(events), event_count + 1)
        self.assertEqual(
            events[-1],
            (
                "flow_landed",
                "waiting_owner",
                "landed",
                "external_landing_completed",
            ),
        )
        self.assertIsNone(
            self.runtime.project_status(str(self.project_root))["data"]["active_flow"]
        )
        replacement = self.runtime.flow_start(
            str(self.project_root), "quick", "Next flow"
        )
        self.assertTrue(replacement["ok"], replacement)

    def test_confirmed_plan_is_compact_recoverable_and_enables_claim(self) -> None:
        flow = self.start_ready_wave()

        result = self.runtime.wave_plan_set(
            str(self.project_root),
            flow_id=flow["id"],
            expected_revision=0,
            packages=self.plan(),
        )

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["data"]["revision"], 1)
        self.assertEqual(result["data"]["package_count"], 3)
        self.assertEqual(result["data"]["current_wave"], 0)
        self.assertEqual(result["data"]["ready_packages"], ["P"])
        self.assertEqual(
            result["next_action"],
            {"tool": "flow_claim", "reason_code": "flow_ready"},
        )
        serialized = repr(result)
        self.assertNotIn("src/contracts.py", serialized)
        self.assertNotIn("python -c", serialized)

        package = self.runtime.work_package_status(
            str(self.project_root), flow["id"], "P"
        )
        self.assertTrue(package["ok"])
        self.assertEqual(package["data"]["package"]["id"], "P")
        self.assertEqual(
            package["data"]["package"]["allowed_paths"], ["src/contracts.py"]
        )
        self.assertNotIn("Q", repr(package["data"]["package"]))

        claimed = self.runtime.flow_claim(str(self.project_root), flow["id"])
        self.assertTrue(claimed["ok"])
        self.assertEqual(claimed["data"]["flow"]["state"], "implementing")

    def test_plan_validation_is_atomic_for_dependency_wave_and_scope_errors(
        self,
    ) -> None:
        cases: list[tuple[str, list[dict], str]] = []

        missing = self.plan()
        missing[1]["dependencies"] = ["MISSING"]
        cases.append(("missing", missing, "package_dependency_missing"))

        cycle = self.plan()
        cycle[0]["dependencies"] = ["Q"]
        cycle[1]["dependencies"] = ["P"]
        cases.append(("cycle", cycle, "package_dependency_cycle"))

        bad_wave = self.plan()
        bad_wave[1]["wave"] = 0
        cases.append(("wave", bad_wave, "package_wave_invalid"))

        conflict = self.plan()
        conflict[1]["dependencies"] = []
        conflict[1]["wave"] = 0
        conflict[1]["allowed_paths"] = ["src/contracts.py"]
        cases.append(("scope", conflict, "package_scope_conflict"))

        for index, (_, packages, error_code) in enumerate(cases):
            with self.subTest(error_code=error_code):
                project, flow = self.new_ready_wave(f"invalid-{index}")
                result = self.runtime.wave_plan_set(
                    str(project),
                    flow_id=flow["id"],
                    expected_revision=0,
                    packages=packages,
                )
                self.assert_error(result, error_code)
                status = self.runtime.project_status(str(project))
                self.assertEqual(status["data"]["wave_plan"]["revision"], 0)
                self.assertEqual(status["data"]["wave_plan"]["package_count"], 0)

    def test_package_sequence_unlocks_one_wave_and_final_gate(self) -> None:
        flow = self.start_implementing_wave()

        premature = self.runtime.gate_run(str(self.project_root), flow["id"])
        self.assert_error(premature, "wave_packages_incomplete")

        self.complete_package(flow["id"], "P", "src/contracts.py")
        status = self.runtime.project_status(str(self.project_root))
        self.assertEqual(status["data"]["wave_plan"]["current_wave"], 1)
        self.assertEqual(status["data"]["wave_plan"]["ready_packages"], ["Q", "R"])
        self.assertEqual(
            status["next_action"],
            {
                "tool": "work_package_status",
                "reason_code": "execute_current_wave",
            },
        )

        self.complete_package(flow["id"], "Q", "src/backend.py")
        self.complete_package(flow["id"], "R", "src/frontend.ts")

        ready_to_gate = self.runtime.project_status(str(self.project_root))
        self.assertIsNone(ready_to_gate["data"]["wave_plan"]["current_wave"])
        self.assertEqual(
            ready_to_gate["next_action"],
            {"tool": "gate_run", "reason_code": "implementation_complete"},
        )
        gated = self.runtime.gate_run(str(self.project_root), flow["id"])
        self.assertTrue(gated["ok"])
        self.assertTrue(gated["data"]["passed"])

    def test_submit_rejects_declared_files_outside_scope_without_state_change(
        self,
    ) -> None:
        flow = self.start_implementing_wave()
        started = self.record(flow["id"], "P", "start")
        self.assertTrue(started["ok"])

        result = self.record(
            flow["id"],
            "P",
            "submit",
            base_commit="a" * 40,
            head_commit="b" * 40,
            changed_files=["src/outside.py"],
            checks=[{"check_id": "unit", "passed": True, "reason_code": "passed"}],
            known_limits=[],
        )

        self.assert_error(result, "package_changed_files_out_of_scope")
        status = self.runtime.work_package_status(
            str(self.project_root), flow["id"], "P"
        )
        self.assertEqual(status["data"]["package"]["status"], "running")

    def test_forbidden_path_can_exclude_a_file_inside_an_allowed_directory(
        self,
    ) -> None:
        flow = self.start_ready_wave()
        package = {
            **self.plan()[0],
            "allowed_paths": ["src/"],
            "forbidden_paths": ["src/secrets.py"],
        }
        planned = self.runtime.wave_plan_set(
            str(self.project_root), flow["id"], 0, [package]
        )
        self.assertTrue(planned["ok"], planned)
        self.assertTrue(
            self.runtime.flow_claim(str(self.project_root), flow["id"])["ok"]
        )
        self.assertTrue(self.record(flow["id"], "P", "start")["ok"])

        forbidden = self.record(
            flow["id"],
            "P",
            "submit",
            base_commit="a" * 40,
            head_commit="b" * 40,
            changed_files=["src/secrets.py"],
            checks=[{"check_id": "unit", "passed": True, "reason_code": "passed"}],
            known_limits=[],
        )
        self.assert_error(forbidden, "package_changed_files_out_of_scope")
        self.assertEqual(
            self.runtime.work_package_status(str(self.project_root), flow["id"], "P")[
                "data"
            ]["package"]["status"],
            "running",
        )

        allowed = self.record(
            flow["id"],
            "P",
            "submit",
            base_commit="a" * 40,
            head_commit="b" * 40,
            changed_files=["src/app.py"],
            checks=[{"check_id": "unit", "passed": True, "reason_code": "passed"}],
            known_limits=[],
        )
        self.assertTrue(allowed["ok"], allowed)

    def test_interrupted_assignment_can_be_retried_without_losing_contract(
        self,
    ) -> None:
        flow = self.start_implementing_wave()
        first = self.record(flow["id"], "P", "start")
        self.assertEqual(first["data"]["package"]["attempt_count"], 1)

        invalid = self.record(
            flow["id"],
            "P",
            "interrupt",
            reason_code="host_interrupted",
            retryable=True,
            changed_files=["src/outside.py"],
        )
        self.assert_error(invalid, "package_changed_files_out_of_scope")

        interrupted = self.record(
            flow["id"],
            "P",
            "interrupt",
            reason_code="host_interrupted",
            retryable=True,
            base_commit="a" * 40,
            head_commit="b" * 40,
            changed_files=["src/contracts.py"],
        )
        self.assertTrue(interrupted["ok"])
        self.assertEqual(interrupted["data"]["package"]["status"], "ready")
        self.assertEqual(interrupted["data"]["package"]["attempt_count"], 1)
        self.assertEqual(interrupted["data"]["package"]["base_commit"], "a" * 40)
        self.assertEqual(interrupted["data"]["package"]["head_commit"], "b" * 40)
        self.assertEqual(
            interrupted["data"]["package"]["changed_files"], ["src/contracts.py"]
        )

        second = self.record(flow["id"], "P", "start")
        self.assertTrue(second["ok"])
        self.assertEqual(second["data"]["package"]["attempt_count"], 2)
        self.assertEqual(second["data"]["package"]["purpose"], "Freeze contracts")

    def test_replan_preserves_integrated_packages_and_rejects_their_mutation(
        self,
    ) -> None:
        flow = self.start_implementing_wave()
        self.complete_package(flow["id"], "P", "src/contracts.py")

        revised = [self.plan()[0], self.package_s()]
        result = self.runtime.wave_plan_set(
            str(self.project_root),
            flow_id=flow["id"],
            expected_revision=1,
            packages=revised,
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["data"]["revision"], 2)
        self.assertEqual(result["data"]["ready_packages"], ["S"])
        with closing(
            sqlite3.connect(self.project_root / ".onlyiflow/onlyiflow.db")
        ) as connection:
            previous = dict(
                connection.execute(
                    """
                    SELECT package_id, status FROM work_packages
                    WHERE flow_id = ? AND revision = 1
                    """,
                    (flow["id"],),
                ).fetchall()
            )
            superseded_events = connection.execute(
                """
                SELECT COUNT(*) FROM package_events
                WHERE flow_id = ? AND revision = 1
                  AND event_type = 'package_superseded'
                """,
                (flow["id"],),
            ).fetchone()[0]
        self.assertEqual(
            previous,
            {"P": "integrated", "Q": "superseded", "R": "superseded"},
        )
        self.assertEqual(superseded_events, 2)

        changed = [dict(revised[0]), revised[1]]
        changed[0] = {**changed[0], "purpose": "Silently changed contract"}
        rejected = self.runtime.wave_plan_set(
            str(self.project_root),
            flow_id=flow["id"],
            expected_revision=2,
            packages=changed,
        )
        self.assert_error(rejected, "integrated_package_immutable")
        status = self.runtime.project_status(str(self.project_root))
        self.assertEqual(status["data"]["wave_plan"]["revision"], 2)

    def test_replan_rejects_busy_and_stale_revisions_atomically(self) -> None:
        flow = self.start_implementing_wave()
        self.assertTrue(self.record(flow["id"], "P", "start")["ok"])

        busy = self.runtime.wave_plan_set(
            str(self.project_root),
            flow_id=flow["id"],
            expected_revision=1,
            packages=self.plan(),
        )
        self.assert_error(busy, "wave_plan_revision_busy")
        current = self.runtime.project_status(str(self.project_root))
        self.assertEqual(current["data"]["wave_plan"]["revision"], 1)
        self.assertEqual(current["data"]["wave_plan"]["package_count"], 3)

        self.assertTrue(
            self.record(
                flow["id"],
                "P",
                "interrupt",
                reason_code="host_interrupted",
                retryable=True,
            )["ok"]
        )
        stale = self.runtime.wave_plan_set(
            str(self.project_root),
            flow_id=flow["id"],
            expected_revision=0,
            packages=self.plan(),
        )
        self.assert_error(stale, "wave_plan_revision_conflict")
        after = self.runtime.project_status(str(self.project_root))
        self.assertEqual(after["data"]["wave_plan"]["revision"], 1)

    def test_review_changes_and_resubmission_preserve_attempt_evidence(self) -> None:
        flow = self.start_implementing_wave()
        self.assertTrue(self.record(flow["id"], "P", "start")["ok"])
        first = self.record(
            flow["id"],
            "P",
            "submit",
            base_commit="a" * 40,
            head_commit="b" * 40,
            changed_files=["src/contracts.py"],
            checks=[{"check_id": "unit", "passed": False, "reason_code": "failed"}],
            known_limits=["Review is pending"],
        )
        self.assertTrue(first["ok"], first)
        rejected_accept = self.record(flow["id"], "P", "accept")
        self.assert_error(rejected_accept, "package_checks_failed")
        requested = self.record(
            flow["id"], "P", "request_changes", reason_code="review_failed"
        )
        self.assertTrue(requested["ok"], requested)
        self.assertEqual(requested["data"]["package"]["status"], "changes_requested")

        restarted = self.record(flow["id"], "P", "start")
        self.assertTrue(restarted["ok"], restarted)
        self.assertEqual(restarted["data"]["package"]["attempt_count"], 1)
        second = self.record(
            flow["id"],
            "P",
            "submit",
            base_commit="a" * 40,
            head_commit="c" * 40,
            changed_files=["src/contracts.py"],
            checks=[{"check_id": "unit", "passed": True, "reason_code": "passed"}],
            known_limits=[],
        )
        self.assertTrue(second["ok"], second)
        self.assertEqual(second["data"]["package"]["head_commit"], "c" * 40)

    def test_conditional_package_can_be_deferred_before_final_gate(self) -> None:
        flow = self.start_ready_wave()
        conditional = {
            **self.plan()[0],
            "condition": {
                "evidence": "Legacy mode is enabled",
                "on_false": "deferred",
            },
        }
        planned = self.runtime.wave_plan_set(
            str(self.project_root), flow["id"], 0, [conditional]
        )
        self.assertTrue(planned["ok"], planned)
        self.assertTrue(
            self.runtime.flow_claim(str(self.project_root), flow["id"])["ok"]
        )

        deferred = self.record(
            flow["id"], "P", "defer", reason_code="condition_not_met"
        )
        self.assertTrue(deferred["ok"], deferred)
        self.assertEqual(deferred["data"]["package"]["status"], "deferred")
        self.assertIsNone(deferred["data"]["wave_plan"]["current_wave"])
        gated = self.runtime.gate_run(str(self.project_root), flow["id"])
        self.assertTrue(gated["ok"], gated)
        self.assertTrue(gated["data"]["passed"])

    def test_package_records_fail_closed_on_extra_or_invalid_fields(self) -> None:
        flow = self.start_implementing_wave()
        extra = self.record(flow["id"], "P", "start", reason_code="unexpected_field")
        self.assert_error(extra, "package_action_fields_invalid")
        self.assertEqual(
            self.runtime.work_package_status(str(self.project_root), flow["id"], "P")[
                "data"
            ]["package"]["status"],
            "ready",
        )

        self.assertTrue(self.record(flow["id"], "P", "start")["ok"])
        invalid_limits = self.record(
            flow["id"],
            "P",
            "submit",
            base_commit="a" * 40,
            head_commit="b" * 40,
            changed_files=["src/contracts.py"],
            checks=[{"check_id": "unit", "passed": True, "reason_code": "passed"}],
            known_limits=[""],
        )
        self.assert_error(invalid_limits, "package_known_limits_invalid")
        self.assertEqual(invalid_limits["next_action"]["tool"], "work_package_status")

        mismatched_checks = self.record(
            flow["id"],
            "P",
            "submit",
            base_commit="a" * 40,
            head_commit="b" * 40,
            changed_files=["src/contracts.py"],
            checks=[
                {
                    "check_id": "undeclared-check",
                    "passed": True,
                    "reason_code": "passed",
                }
            ],
            known_limits=[],
        )
        self.assert_error(mismatched_checks, "package_checks_mismatch")

    def test_v1_status_is_read_only_then_mutation_migrates_additively(self) -> None:
        project = Path(self.temporary.name) / "legacy v1"
        state_root = project / ".onlyiflow"
        specs = state_root / "specs"
        specs.mkdir(parents=True)
        (state_root / "config.toml").write_text(
            "version = 1\nchecks = []\n", encoding="utf-8"
        )
        database = state_root / "onlyiflow.db"
        with closing(sqlite3.connect(database)) as connection:
            connection.executescript(
                """
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
                PRAGMA user_version = 1;
                """
            )
            connection.execute(
                """
                INSERT INTO flows VALUES (
                    'legacy-flow', 'quick', 'Preserved flow', 'implementing',
                    '2026-07-19T00:00:00+00:00', '2026-07-19T00:00:00+00:00'
                )
                """
            )
            connection.execute(
                """
                INSERT INTO domain_events (
                    flow_id, event_type, from_state, to_state, created_at
                ) VALUES (
                    'legacy-flow', 'flow_claimed', 'ready', 'implementing',
                    '2026-07-19T00:00:00+00:00'
                )
                """
            )
            connection.commit()

        before_status = database.read_bytes()
        runtime = Runtime()
        status = runtime.project_status(str(project))
        self.assertTrue(status["ok"], status)
        self.assertEqual(status["data"]["active_flow"]["id"], "legacy-flow")
        self.assertEqual(status["data"]["active_flow"]["mode"], "direct")
        self.assertIsNone(status["data"]["wave_plan"])
        package = runtime.work_package_status(str(project), "0" * 32, "P")
        self.assert_error(package, "package_not_found")
        self.assertEqual(database.read_bytes(), before_status)
        with closing(sqlite3.connect(database)) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 1)
            self.assertEqual(
                {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                },
                {"flows", "specs", "gates", "domain_events"},
            )

        configured = runtime.gate_configure(
            str(project),
            [
                {
                    "id": "tests",
                    "required": True,
                    "command": ["python", "-c", "pass"],
                    "timeout_seconds": 10,
                }
            ],
        )
        self.assertTrue(configured["ok"], configured)
        with closing(sqlite3.connect(database)) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            flow_count = connection.execute("SELECT COUNT(*) FROM flows").fetchone()[0]
            event_count = connection.execute(
                "SELECT COUNT(*) FROM domain_events"
            ).fetchone()[0]
            event_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(domain_events)")
            }
        self.assertEqual(version, 3)
        self.assertTrue(
            {"wave_plans", "work_packages", "package_dependencies", "package_events"}
            <= tables
        )
        self.assertEqual(flow_count, 1)
        self.assertEqual(event_count, 1)
        self.assertIn("reason_code", event_columns)

    def test_direct_quick_flow_keeps_the_existing_path(self) -> None:
        project = Path(self.temporary.name) / "direct"
        project.mkdir()
        self.runtime.project_init(str(project))
        self.runtime.gate_configure(
            str(project),
            [
                {
                    "id": "tests",
                    "required": True,
                    "command": ["python", "-c", "pass"],
                    "timeout_seconds": 10,
                }
            ],
        )

        started = self.runtime.flow_start(str(project), "quick", "Direct quick")
        self.assertTrue(started["ok"])
        self.assertEqual(started["data"]["flow"]["mode"], "direct")
        self.assertNotIn("next_action", started)
        status = self.runtime.project_status(str(project))
        self.assertIsNone(status["data"]["wave_plan"])
        self.assertEqual(
            status["next_action"],
            {"tool": "gate_run", "reason_code": "implementation_active"},
        )

    def start_wave(self, *, risk: str = "deep") -> dict:
        result = self.runtime.flow_start(
            str(self.project_root),
            risk=risk,
            title="Wave goal",
            mode="wave",
        )
        self.assertTrue(result["ok"], result)
        return result["data"]["flow"]

    def start_ready_wave(self) -> dict:
        flow = self.start_wave()
        self.assertTrue(self.submit_spec(flow["id"])["ok"])
        return flow

    def start_implementing_wave(self) -> dict:
        flow = self.start_ready_wave()
        planned = self.runtime.wave_plan_set(
            str(self.project_root), flow["id"], 0, self.plan()
        )
        self.assertTrue(planned["ok"], planned)
        claimed = self.runtime.flow_claim(str(self.project_root), flow["id"])
        self.assertTrue(claimed["ok"], claimed)
        return flow

    def submit_spec(self, flow_id: str) -> dict:
        return self.runtime.spec_submit(
            str(self.project_root),
            flow_id,
            "Deliver the Wave goal",
            "All packages integrate and the final Gate passes",
            "The host owns agents, worktrees and Git",
            ["src/contracts.py", "src/backend.py", "src/frontend.ts"],
        )

    def complete_package(
        self, flow_id: str, package_id: str, changed_file: str
    ) -> None:
        package = self.runtime.work_package_status(
            str(self.project_root), flow_id, package_id
        )["data"]["package"]
        self.assertTrue(self.record(flow_id, package_id, "start")["ok"])
        submitted = self.record(
            flow_id,
            package_id,
            "submit",
            base_commit="a" * 40,
            head_commit="b" * 40,
            changed_files=[changed_file],
            checks=[
                {
                    "check_id": package["check_ids"][0],
                    "passed": True,
                    "reason_code": "passed",
                }
            ],
            known_limits=[],
        )
        self.assertTrue(submitted["ok"], submitted)
        self.assertTrue(self.record(flow_id, package_id, "accept")["ok"])
        self.assertTrue(
            self.record(
                flow_id,
                package_id,
                "integrate",
                head_commit="b" * 40,
            )["ok"]
        )

    def record(
        self, flow_id: str, package_id: str, action: str, **kwargs: object
    ) -> dict:
        return self.runtime.work_package_record(
            str(self.project_root),
            flow_id=flow_id,
            package_id=package_id,
            action=action,
            **kwargs,
        )

    def plan(self) -> list[dict]:
        return [
            {
                "id": "P",
                "slug": "contract",
                "title": "Freeze contract",
                "purpose": "Freeze contracts",
                "baseline_assumptions": ["The current contract is the baseline"],
                "wave": 0,
                "dependencies": [],
                "allowed_paths": ["src/contracts.py"],
                "forbidden_paths": [],
                "deliverables": ["Stable contract"],
                "non_goals": ["No host configuration"],
                "acceptance": ["unit check passes"],
                "check_ids": ["unit"],
                "runtime_boundaries": ["offline"],
                "requires_authorization": [],
                "requires_independent_review": False,
                "condition": None,
            },
            {
                "id": "Q",
                "slug": "backend",
                "title": "Implement backend",
                "purpose": "Implement backend against P",
                "baseline_assumptions": ["Integrated P is the backend baseline"],
                "wave": 1,
                "dependencies": ["P"],
                "allowed_paths": ["src/backend.py"],
                "forbidden_paths": [],
                "deliverables": ["Backend behavior"],
                "non_goals": ["No frontend changes"],
                "acceptance": ["backend check passes"],
                "check_ids": ["backend-check"],
                "runtime_boundaries": ["offline"],
                "requires_authorization": [],
                "requires_independent_review": False,
                "condition": None,
            },
            {
                "id": "R",
                "slug": "frontend",
                "title": "Implement frontend",
                "purpose": "Implement frontend against P",
                "baseline_assumptions": ["Integrated P is the frontend baseline"],
                "wave": 1,
                "dependencies": ["P"],
                "allowed_paths": ["src/frontend.ts"],
                "forbidden_paths": [],
                "deliverables": ["Frontend behavior"],
                "non_goals": ["No backend changes"],
                "acceptance": ["frontend check passes"],
                "check_ids": ["frontend-check"],
                "runtime_boundaries": ["offline"],
                "requires_authorization": [],
                "requires_independent_review": False,
                "condition": None,
            },
        ]

    def package_s(self) -> dict:
        return {
            "id": "S",
            "slug": "audit",
            "title": "Integrate audit",
            "purpose": "Integrate the revised downstream package",
            "baseline_assumptions": ["Integrated P is the audit baseline"],
            "wave": 1,
            "dependencies": ["P"],
            "allowed_paths": ["src/audit.py"],
            "forbidden_paths": [],
            "deliverables": ["Audit behavior"],
            "non_goals": ["No contract changes"],
            "acceptance": ["audit check passes"],
            "check_ids": ["audit-check"],
            "runtime_boundaries": ["offline"],
            "requires_authorization": [],
            "requires_independent_review": True,
            "condition": None,
        }

    def new_ready_wave(self, name: str) -> tuple[Path, dict]:
        project = Path(self.temporary.name) / name
        project.mkdir()
        runtime = Runtime()
        runtime.project_init(str(project))
        runtime.gate_configure(
            str(project),
            [
                {
                    "id": "tests",
                    "required": True,
                    "command": ["python", "-c", "pass"],
                    "timeout_seconds": 10,
                }
            ],
        )
        flow = runtime.flow_start(str(project), "deep", "Wave", mode="wave")["data"][
            "flow"
        ]
        runtime.spec_submit(
            str(project),
            flow["id"],
            "Goal",
            "Acceptance",
            "Boundaries",
            ["src/app.py"],
        )
        return project, flow

    def assert_error(self, result: dict, code: str) -> None:
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["error"]["code"], code)


if __name__ == "__main__":
    unittest.main()
