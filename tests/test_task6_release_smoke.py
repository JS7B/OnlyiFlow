from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import support  # noqa: F401  # Adds the repository source root to sys.path.

from scripts.run_release_smoke import (
    EXPECTED_SEQUENCES,
    REQUIRED_CHECKS,
    build_report,
    release_project,
)


class Task6ReleaseSmokeTests(unittest.TestCase):
    def test_release_smoke_requires_owner_confirmed_gate_configuration(self) -> None:
        self.assertEqual(
            EXPECTED_SEQUENCES["gate_configuration_request"],
            ("project_status",),
        )
        self.assertEqual(
            EXPECTED_SEQUENCES["gate_configuration_confirmation"],
            ("project_status", "gate_configure"),
        )
        self.assertIn(
            "gate_configuration_waited_for_confirmation",
            REQUIRED_CHECKS,
        )
        runner = (
            Path(__file__).resolve().parents[1] / "scripts/run_release_smoke.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("write_gate_config(project)", runner)

    def test_report_requires_every_check_sequence_and_cleanup(self) -> None:
        checks = {check: True for check in REQUIRED_CHECKS}
        sequences = {label: list(tools) for label, tools in EXPECTED_SEQUENCES.items()}

        passed = build_report(
            host="codex",
            checks=checks,
            sequences=sequences,
            cleanup_errors=[],
            error=None,
        )

        self.assertEqual(passed["status"], "passed")
        self.assertTrue(all(passed["checks"].values()))
        self.assertEqual(passed["sequences"], sequences)
        self.assertEqual(passed["cleanup_errors"], [])

        checks["landing_waiting_owner"] = False
        failed_check = build_report(
            host="codex",
            checks=checks,
            sequences=sequences,
            cleanup_errors=[],
            error="landing_state_mismatch",
        )
        self.assertEqual(failed_check["status"], "failed")

        checks["landing_waiting_owner"] = True
        sequences["quick_start"] = ["project_status"]
        failed_sequence = build_report(
            host="codex",
            checks=checks,
            sequences=sequences,
            cleanup_errors=[],
            error="quick_start_sequence_mismatch",
        )
        self.assertEqual(failed_sequence["status"], "failed")

        sequences["quick_start"] = list(EXPECTED_SEQUENCES["quick_start"])
        failed_cleanup = build_report(
            host="codex",
            checks=checks,
            sequences=sequences,
            cleanup_errors=["codex_lifecycle_cleanup_failed"],
            error=None,
        )
        self.assertEqual(failed_cleanup["status"], "failed")

    def test_report_is_content_free_and_uses_only_approved_evidence(self) -> None:
        report = build_report(
            host="claude",
            checks={check: True for check in REQUIRED_CHECKS},
            sequences={
                label: list(tools) for label, tools in EXPECTED_SEQUENCES.items()
            },
            cleanup_errors=[],
            error=None,
        )

        self.assertEqual(
            set(report),
            {
                "host",
                "generated_at",
                "status",
                "checks",
                "sequences",
                "cleanup_errors",
            },
        )
        serialized = json.dumps(report).casefold()
        for prohibited in [
            "prompt",
            "assistant",
            "command",
            "cwd",
            "stdout",
            "stderr",
            "transcript",
            "credential",
            "project_root",
        ]:
            self.assertNotIn(prohibited, serialized)

    def test_release_project_is_a_disposable_git_project_with_spaces(self) -> None:
        with release_project() as project:
            root = project.parent
            self.assertEqual(root.parent, Path(tempfile.gettempdir()).resolve())
            self.assertIn(" ", project.name)
            self.assertTrue((project / ".git").is_dir())
            self.assertTrue((project / "app.py").is_file())
            self.assertTrue((project / "tests/test_app.py").is_file())
            self.assertFalse((project / ".onlyiflow").exists())

        self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
