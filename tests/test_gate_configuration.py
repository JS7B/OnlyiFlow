from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import tomllib
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import support  # noqa: F401  # Adds the repository source root to sys.path.

from onlyiflow.runtime import Runtime


class GateConfigurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="OnlyiFlow gate configuration "
        )
        self.addCleanup(self.temporary.cleanup)
        self.project_root = Path(self.temporary.name) / "project with spaces"
        self.project_root.mkdir()
        self.runtime = Runtime()
        initialized = self.runtime.project_init(str(self.project_root))
        self.assertTrue(initialized["ok"])

    def test_status_reports_unconfigured_gate_without_changing_config(self) -> None:
        before = self.config.read_bytes()

        result = self.runtime.project_status(str(self.project_root))

        self.assertTrue(result["ok"])
        self.assertEqual(
            result["data"]["gate_config"],
            {
                "configured": False,
                "check_count": 0,
                "required_count": 0,
            },
        )
        self.assertEqual(
            result["next_action"],
            {
                "tool": "gate_configure",
                "reason_code": "gate_configuration_required",
            },
        )
        self.assertEqual(self.config.read_bytes(), before)

    def test_valid_configuration_is_atomic_private_and_ready(self) -> None:
        secret = "SECRET_GATE_COMMAND"
        checks = [
            {
                "id": "tests",
                "required": True,
                "command": [sys.executable, "-c", f"print('{secret}')"],
                "timeout_seconds": 120,
            },
            {
                "id": "lint",
                "required": False,
                "command": [sys.executable, "-c", "pass"],
                "timeout_seconds": 30,
            },
        ]

        with (
            patch("onlyiflow.gates.os.replace", wraps=os.replace) as replace,
            patch("onlyiflow.gates.subprocess.run") as run,
        ):
            result = self.runtime.gate_configure(str(self.project_root), checks)

        self.assertTrue(result["ok"])
        self.assertEqual(
            result["data"],
            {
                "checks": [
                    {
                        "check_id": "tests",
                        "required": True,
                        "timeout_seconds": 120,
                    },
                    {
                        "check_id": "lint",
                        "required": False,
                        "timeout_seconds": 30,
                    },
                ],
                "check_count": 2,
                "required_count": 1,
            },
        )
        self.assertEqual(
            result["next_action"],
            {"tool": "flow_start", "reason_code": "project_ready"},
        )
        serialized = json.dumps(result)
        self.assertNotIn(secret, serialized)
        self.assertNotIn(sys.executable, serialized)
        self.assertNotIn(str(self.project_root), serialized)
        run.assert_not_called()
        replace.assert_called_once()
        source, destination = replace.call_args.args
        self.assertTrue(os.path.samefile(Path(source).parent, self.config.parent))
        self.assertTrue(os.path.samefile(destination, self.config))
        self.assertEqual(
            list(self.config.parent.glob(".config.toml.*.tmp")),
            [],
        )

        with self.config.open("rb") as source_file:
            self.assertEqual(
                tomllib.load(source_file),
                {"version": 1, "checks": checks},
            )
        status = self.runtime.project_status(str(self.project_root))
        self.assertEqual(
            status["data"]["gate_config"],
            {
                "configured": True,
                "check_count": 2,
                "required_count": 1,
            },
        )
        self.assertEqual(
            status["next_action"],
            {"tool": "flow_start", "reason_code": "project_ready"},
        )
        self.assertNotIn(secret.encode(), self.database.read_bytes())
        with closing(sqlite3.connect(self.database)) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM domain_events").fetchone()[0],
                0,
            )

    def test_invalid_configuration_preserves_existing_bytes(self) -> None:
        original = self.config.read_bytes()
        invalid_cases = [
            [],
            [self.check("duplicate"), self.check("duplicate")],
            [{**self.check("bad-command"), "command": "python -m unittest"}],
            [{**self.check("bad-timeout"), "timeout_seconds": 0}],
            [self.check(f"check-{index}") for index in range(33)],
        ]

        for checks in invalid_cases:
            with self.subTest(checks=checks):
                result = self.runtime.gate_configure(str(self.project_root), checks)

                self.assertFalse(result["ok"])
                self.assertEqual(result["error"]["code"], "gate_config_invalid")
                self.assertEqual(self.config.read_bytes(), original)

    def test_atomic_replace_failure_preserves_existing_bytes_and_cleans_temp(
        self,
    ) -> None:
        original = self.config.read_bytes()

        with patch("onlyiflow.gates.os.replace", side_effect=OSError("replace failed")):
            result = self.runtime.gate_configure(
                str(self.project_root), [self.check("tests")]
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "runtime_error")
        self.assertEqual(self.config.read_bytes(), original)
        self.assertEqual(list(self.config.parent.glob(".config.toml.*.tmp")), [])

    def test_active_flow_locks_configuration_and_preserves_existing_bytes(self) -> None:
        configured = self.runtime.gate_configure(
            str(self.project_root), [self.check("tests")]
        )
        self.assertTrue(configured["ok"])
        before = self.config.read_bytes()
        started = self.runtime.flow_start(
            str(self.project_root), risk="quick", title="Locked configuration"
        )
        self.assertTrue(started["ok"])

        result = self.runtime.gate_configure(
            str(self.project_root), [self.check("replacement")]
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "gate_config_locked")
        self.assertEqual(
            result["next_action"],
            {"tool": "project_status", "reason_code": "resume_active_flow"},
        )
        self.assertEqual(self.config.read_bytes(), before)

    def test_legacy_active_flow_can_configure_its_first_gate_once(self) -> None:
        configured = self.runtime.gate_configure(
            str(self.project_root), [self.check("initial")]
        )
        self.assertTrue(configured["ok"])
        started = self.runtime.flow_start(
            str(self.project_root), risk="quick", title="Legacy active flow"
        )
        self.assertTrue(started["ok"])
        flow = started["data"]["flow"]
        self.config.write_text("version = 1\nchecks = []\n", encoding="utf-8")

        status = self.runtime.project_status(str(self.project_root))

        self.assertEqual(status["data"]["active_flow"], flow)
        self.assertEqual(
            status["next_action"],
            {
                "tool": "gate_configure",
                "reason_code": "gate_configuration_required",
            },
        )
        missing = self.runtime.gate_run(str(self.project_root), flow["id"])
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["error"]["code"], "gate_checks_missing")
        self.assertEqual(
            missing["next_action"],
            {
                "tool": "gate_configure",
                "reason_code": "gate_configuration_required",
            },
        )

        migrated = self.runtime.gate_configure(
            str(self.project_root), [self.check("regression")]
        )

        self.assertTrue(migrated["ok"])
        self.assertEqual(
            migrated["next_action"],
            {"tool": "gate_run", "reason_code": "implementation_active"},
        )
        resumed = self.runtime.project_status(str(self.project_root))
        self.assertEqual(resumed["data"]["active_flow"], flow)
        self.assertEqual(resumed["next_action"], migrated["next_action"])
        before = self.config.read_bytes()
        locked = self.runtime.gate_configure(
            str(self.project_root), [self.check("replacement")]
        )
        self.assertFalse(locked["ok"])
        self.assertEqual(locked["error"]["code"], "gate_config_locked")
        self.assertEqual(self.config.read_bytes(), before)

    def test_unconfigured_project_cannot_start_a_flow(self) -> None:
        before = self.config.read_bytes()

        result = self.runtime.flow_start(
            str(self.project_root), risk="quick", title="Missing Gate"
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "gate_checks_missing")
        self.assertEqual(
            result["next_action"],
            {
                "tool": "gate_configure",
                "reason_code": "gate_configuration_required",
            },
        )
        self.assertEqual(self.config.read_bytes(), before)
        status = self.runtime.project_status(str(self.project_root))
        self.assertIsNone(status["data"]["active_flow"])

    def check(self, check_id: str) -> dict:
        return {
            "id": check_id,
            "required": True,
            "command": [sys.executable, "-c", "pass"],
            "timeout_seconds": 10,
        }

    @property
    def config(self) -> Path:
        return self.project_root / ".onlyiflow/config.toml"

    @property
    def database(self) -> Path:
        return self.project_root / ".onlyiflow/onlyiflow.db"


if __name__ == "__main__":
    unittest.main()
