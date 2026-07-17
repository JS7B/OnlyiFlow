from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import support  # noqa: F401  # Adds the repository source root to sys.path.

from onlyiflow.runtime import Runtime


class GateRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="OnlyiFlow gate runtime ")
        self.addCleanup(self.temporary.cleanup)
        self.project_root = Path(self.temporary.name) / "project with spaces"
        self.project_root.mkdir()
        self.runtime = Runtime()
        self.assertTrue(self.runtime.project_init(str(self.project_root))["ok"])
        self.flow = self.runtime.flow_start(
            str(self.project_root),
            risk="quick",
            title="Gate behavior",
        )["data"]["flow"]

    def test_required_failure_remains_implementing_and_keeps_evidence_private(
        self,
    ) -> None:
        secret = "SECRET_GATE_OUTPUT"
        self.write_checks(
            [
                {
                    "id": "tests",
                    "required": True,
                    "command": [
                        sys.executable,
                        "-c",
                        (
                            "import sys;"
                            f"print('{secret}');"
                            f"sys.stderr.write('{secret}');"
                            "sys.exit(7)"
                        ),
                    ],
                    "timeout_seconds": 10,
                }
            ]
        )

        result = self.runtime.gate_run(str(self.project_root), self.flow["id"])

        self.assertTrue(result["ok"])
        self.assertFalse(result["data"]["passed"])
        self.assertEqual(result["data"]["state"], "implementing")
        self.assertEqual(
            self.public_check(result),
            {
                "check_id": "tests",
                "required": True,
                "passed": False,
                "reason_code": "check_failed",
                "exit_code": 7,
            },
        )
        self.assertEqual(
            result["next_action"],
            {"tool": "gate_run", "reason_code": "required_check_failed"},
        )
        serialized = json.dumps(result)
        self.assertNotIn(secret, serialized)
        self.assertNotIn(str(self.project_root), serialized)
        self.assertNotIn(sys.executable, serialized)
        self.assert_database_has_no_raw_command_data(secret)
        self.assertEqual(self.flow_state(), "implementing")
        self.assert_events(
            [
                ("flow_started", None, "implementing"),
                ("gate_failed", "implementing", "implementing"),
            ]
        )

    def test_required_pass_with_optional_failure_enters_gate_passed(self) -> None:
        self.write_checks(
            [
                self.python_check("required", required=True, exit_code=0),
                self.python_check("optional", required=False, exit_code=3),
            ]
        )

        result = self.runtime.gate_run(str(self.project_root), self.flow["id"])

        self.assertTrue(result["ok"])
        self.assertTrue(result["data"]["passed"])
        self.assertEqual(result["data"]["state"], "gate_passed")
        self.assertEqual(
            [
                (check["check_id"], check["passed"])
                for check in result["data"]["checks"]
            ],
            [("required", True), ("optional", False)],
        )
        self.assertEqual(
            result["next_action"],
            {"tool": "landing_request", "reason_code": "gates_passed"},
        )
        status = self.runtime.project_status(str(self.project_root))
        self.assertEqual(status["data"]["latest_gate"]["passed"], True)
        self.assertEqual(
            status["data"]["latest_gate"]["checks"], result["data"]["checks"]
        )
        self.assertEqual(self.flow_state(), "gate_passed")

    def test_failed_gate_can_be_retried_after_implementation_fix(self) -> None:
        self.write_checks([self.python_check("tests", required=True, exit_code=1)])
        failed = self.runtime.gate_run(str(self.project_root), self.flow["id"])
        self.assertFalse(failed["data"]["passed"])

        self.write_checks([self.python_check("tests", required=True, exit_code=0)])
        passed = self.runtime.gate_run(str(self.project_root), self.flow["id"])

        self.assertTrue(passed["data"]["passed"])
        self.assertEqual(self.flow_state(), "gate_passed")
        self.assertEqual(self.gate_run_count(), 2)
        self.assert_events(
            [
                ("flow_started", None, "implementing"),
                ("gate_failed", "implementing", "implementing"),
                ("gate_passed", "implementing", "gate_passed"),
            ]
        )

    def test_timeout_is_compact_failure_without_exit_code(self) -> None:
        self.write_checks(
            [
                {
                    "id": "slow",
                    "required": True,
                    "command": [
                        sys.executable,
                        "-c",
                        "import time; time.sleep(2)",
                    ],
                    "timeout_seconds": 1,
                }
            ]
        )

        result = self.runtime.gate_run(str(self.project_root), self.flow["id"])

        self.assertTrue(result["ok"])
        self.assertEqual(
            self.public_check(result),
            {
                "check_id": "slow",
                "required": True,
                "passed": False,
                "reason_code": "check_timeout",
                "exit_code": None,
            },
        )
        self.assertGreaterEqual(result["data"]["checks"][0]["duration_ms"], 0)

    def test_gate_requires_valid_nonempty_configuration_and_implementing_flow(
        self,
    ) -> None:
        missing_checks = self.runtime.gate_run(str(self.project_root), self.flow["id"])
        self.assert_error(missing_checks, "gate_checks_missing")

        self.config.write_text(
            """
version = 1
[[checks]]
id = "bad"
required = true
command = "python -m unittest"
timeout_seconds = 10
""".strip()
            + "\n",
            encoding="utf-8",
        )
        invalid_config = self.runtime.gate_run(str(self.project_root), self.flow["id"])
        self.assert_error(invalid_config, "gate_config_invalid")

        other_project = self.new_managed_project("draft project")
        draft = self.runtime.flow_start(
            str(other_project), risk="standard", title="Draft"
        )["data"]["flow"]
        self.write_checks(
            [self.python_check("tests", required=True, exit_code=0)],
            project_root=other_project,
        )
        invalid_state = self.runtime.gate_run(str(other_project), draft["id"])
        self.assert_error(invalid_state, "invalid_transition")

        missing_flow = self.runtime.gate_run(str(self.project_root), "f" * 32)
        self.assert_error(missing_flow, "flow_not_found")

    def test_gate_configuration_rejects_more_than_32_checks(self) -> None:
        self.write_checks(
            [
                self.python_check(
                    f"check-{index}",
                    required=True,
                    exit_code=0,
                )
                for index in range(33)
            ]
        )

        result = self.runtime.gate_run(str(self.project_root), self.flow["id"])

        self.assert_error(result, "gate_config_invalid")

    def test_gate_process_uses_no_shell_project_cwd_and_discards_output(self) -> None:
        self.write_checks([self.python_check("tests", required=True, exit_code=0)])
        completed = subprocess.CompletedProcess(
            args=["ignored"],
            returncode=0,
        )

        with patch("onlyiflow.gates.subprocess.run", return_value=completed) as run:
            result = self.runtime.gate_run(str(self.project_root), self.flow["id"])

        self.assertTrue(result["ok"])
        run.assert_called_once()
        args, kwargs = run.call_args
        self.assertEqual(args[0][0], sys.executable)
        self.assertEqual(kwargs["cwd"], self.project_root.resolve())
        self.assertFalse(kwargs["shell"])
        self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
        self.assertIs(kwargs["stdout"], subprocess.DEVNULL)
        self.assertIs(kwargs["stderr"], subprocess.DEVNULL)
        self.assertEqual(kwargs["timeout"], 10)
        self.assertFalse(kwargs["check"])

    def test_landing_request_requires_passed_gate_and_waits_for_owner(self) -> None:
        premature = self.runtime.landing_request(
            str(self.project_root), self.flow["id"]
        )
        self.assert_error(premature, "invalid_transition")

        self.write_checks([self.python_check("tests", required=True, exit_code=0)])
        self.assertTrue(
            self.runtime.gate_run(str(self.project_root), self.flow["id"])["data"][
                "passed"
            ]
        )
        result = self.runtime.landing_request(str(self.project_root), self.flow["id"])

        self.assertTrue(result["ok"])
        self.assertEqual(
            result["data"],
            {
                "flow_id": self.flow["id"],
                "state": "waiting_owner",
                "direct_git_enforcement": False,
            },
        )
        self.assertNotIn("next_action", result)
        self.assertEqual(self.flow_state(), "waiting_owner")
        status = self.runtime.project_status(str(self.project_root))
        self.assertEqual(status["data"]["active_flow"]["state"], "waiting_owner")
        self.assertNotIn("next_action", status)
        self.assert_events(
            [
                ("flow_started", None, "implementing"),
                ("gate_passed", "implementing", "gate_passed"),
                ("landing_requested", "gate_passed", "waiting_owner"),
            ]
        )

    def write_checks(
        self,
        checks: list[dict],
        *,
        project_root: Path | None = None,
    ) -> None:
        root = project_root or self.project_root
        lines = ["version = 1"]
        for check in checks:
            lines.extend(
                [
                    "",
                    "[[checks]]",
                    f"id = {json.dumps(check['id'])}",
                    f"required = {str(check['required']).lower()}",
                    f"command = {json.dumps(check['command'])}",
                    f"timeout_seconds = {check['timeout_seconds']}",
                ]
            )
        (root / ".onlyiflow/config.toml").write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
        )

    def python_check(
        self,
        check_id: str,
        *,
        required: bool,
        exit_code: int,
    ) -> dict:
        return {
            "id": check_id,
            "required": required,
            "command": [
                sys.executable,
                "-c",
                f"import sys; sys.exit({exit_code})",
            ],
            "timeout_seconds": 10,
        }

    def new_managed_project(self, name: str) -> Path:
        project = Path(self.temporary.name) / name
        project.mkdir()
        self.assertTrue(self.runtime.project_init(str(project))["ok"])
        return project

    @property
    def config(self) -> Path:
        return self.project_root / ".onlyiflow/config.toml"

    @property
    def database(self) -> Path:
        return self.project_root / ".onlyiflow/onlyiflow.db"

    def public_check(self, result: dict) -> dict:
        check = result["data"]["checks"][0]
        return {
            key: check[key]
            for key in [
                "check_id",
                "required",
                "passed",
                "reason_code",
                "exit_code",
            ]
        }

    def flow_state(self) -> str:
        with closing(sqlite3.connect(self.database)) as connection:
            return connection.execute(
                "SELECT state FROM flows WHERE id = ?", (self.flow["id"],)
            ).fetchone()[0]

    def gate_run_count(self) -> int:
        with closing(sqlite3.connect(self.database)) as connection:
            return connection.execute(
                "SELECT COUNT(DISTINCT run_id) FROM gates"
            ).fetchone()[0]

    def assert_database_has_no_raw_command_data(self, secret: str) -> None:
        with closing(sqlite3.connect(self.database)) as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(gates)")}
            values = connection.execute(
                """
                SELECT check_id, reason_code
                FROM gates
                """
            ).fetchall()
        self.assertNotIn("command", columns)
        self.assertNotIn("cwd", columns)
        self.assertNotIn("stdout", columns)
        self.assertNotIn("stderr", columns)
        self.assertNotIn(secret, json.dumps(values))

    def assert_events(self, expected: list[tuple[str, str | None, str | None]]) -> None:
        with closing(sqlite3.connect(self.database)) as connection:
            events = connection.execute(
                """
                SELECT event_type, from_state, to_state
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
