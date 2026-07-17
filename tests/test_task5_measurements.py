from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import support

from scripts.run_efficiency_measurements import (
    APPROVED_METRIC_KEYS,
    MeasurementFailure,
    build_report,
    evaluate_budgets,
    gate_evidence_is_private,
    prepare_project,
    regression_passed,
    require_turn,
    source_snapshot,
    summarize_flow,
    task5_preflight,
    task5_host_command,
)


class Task5MeasurementTests(unittest.TestCase):
    def test_turn_sequence_failure_reports_only_expected_and_actual_tools(self) -> None:
        with self.assertRaisesRegex(
            MeasurementFailure,
            r'quick_gate_unexpected_mcp_sequence:expected=\["project_status","gate_run"\],actual=\["project_status"\]',
        ):
            require_turn(
                {"tools": ["project_status"], "edited": False},
                tools=["project_status", "gate_run"],
                edited=False,
                label="quick_gate",
            )

    def test_source_snapshot_excludes_workflow_state_and_bytecode(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            project = Path(root)
            (project / "app.py").write_text("value = 1\n", encoding="utf-8")
            (project / ".onlyiflow").mkdir()
            (project / ".onlyiflow/onlyiflow.db").write_bytes(b"private")
            (project / "__pycache__").mkdir()
            (project / "__pycache__/app.pyc").write_bytes(b"private")

            snapshot = source_snapshot(project)

        self.assertEqual(list(snapshot), ["app.py"])

    def test_flow_summary_counts_calls_before_first_model_edit(self) -> None:
        turns = [
            {"duration_seconds": 1.25, "tools": ["project_status", "flow_start"], "edited": False},
            {"duration_seconds": 2.5, "tools": [], "edited": True},
            {"duration_seconds": 0.75, "tools": ["project_status", "gate_run"], "edited": False},
        ]

        summary = summarize_flow(
            turns,
            gate_failures=1,
            task_success=True,
            regression_passed=True,
        )

        self.assertEqual(
            summary,
            {
                "wall_clock_seconds": 4.5,
                "model_turns": 3,
                "mcp_calls_before_first_code_edit": 2,
                "total_mcp_calls": 4,
                "gate_failures_caught_before_landing": 1,
                "task_success": True,
                "regression_result": "passed",
            },
        )

    def test_acceptance_budgets_require_the_approved_ceremony(self) -> None:
        evidence = {
            "baseline": {"additional_model_turns": 0, "enabled_mcp_calls": 0},
            "initialization": {"reported_separately": True},
            "quick": {
                "start_calls": 2,
                "specs": 0,
                "plans": 0,
                "automatic_review_turns": 0,
                "gate_failed_then_passed": True,
                "gate_evidence_private": True,
            },
            "standard": {
                "specs": 1,
                "automatic_review_turns": 0,
                "gate_failed_then_passed": True,
                "gate_evidence_private": True,
            },
        }

        budgets = evaluate_budgets(evidence)

        self.assertTrue(all(budgets.values()))
        evidence["quick"]["start_calls"] = 3
        self.assertFalse(evaluate_budgets(evidence)["managed_quick_two_call_start"])

    def test_report_contains_only_approved_metrics_and_budget_results(self) -> None:
        metrics = {
            "wall_clock_seconds": 1.0,
            "model_turns": 1,
            "mcp_calls_before_first_code_edit": None,
            "total_mcp_calls": 0,
            "gate_failures_caught_before_landing": 0,
            "task_success": True,
            "regression_result": "not_applicable",
        }
        report = build_report(
            host="codex",
            measurements={
                "baseline_disabled": metrics,
                "baseline_enabled": metrics,
                "initialization": metrics,
                "quick": metrics,
                "standard": metrics,
            },
            budgets={"enabled_uninvoked_zero_overhead": True},
            cleanup_errors=[],
        )

        for measurement in report["measurements"].values():
            self.assertEqual(set(measurement), APPROVED_METRIC_KEYS)
        serialized = str(report).casefold()
        for prohibited in [
            "prompt",
            "stdout",
            "stderr",
            "command",
            "assistant",
            "transcript",
            "project_root",
        ]:
            self.assertNotIn(prohibited, serialized)

    def test_disabled_claude_command_keeps_prompt_outside_allowed_tools(self) -> None:
        command = task5_host_command(
            "claude",
            Path("project"),
            "ordinary prompt",
            enabled=False,
        )

        allowed_index = command.index("--allowedTools")
        disabled_index = command.index("--disable-slash-commands")
        self.assertLess(allowed_index, disabled_index)
        self.assertEqual(
            json.loads(command[command.index("--mcp-config") + 1]),
            {"mcpServers": {}},
        )
        self.assertEqual(
            command[command.index("--mcp-config") + 2],
            "--prompt-suggestions",
        )
        self.assertIn("--strict-mcp-config", command)
        self.assertEqual(
            command[command.index("--prompt-suggestions") + 1],
            "false",
        )
        self.assertEqual(command[-1], "ordinary prompt")

    def test_enabled_claude_command_loads_only_the_explicit_plugin_server(self) -> None:
        command = task5_host_command(
            "claude",
            Path("project"),
            "/onlyiflow:onlyiflow start a quick flow",
            enabled=True,
        )

        config = json.loads(command[command.index("--mcp-config") + 1])
        self.assertEqual(
            set(config["mcpServers"]),
            {"plugin_onlyiflow_onlyiflow"},
        )
        server = config["mcpServers"]["plugin_onlyiflow_onlyiflow"]
        self.assertTrue(Path(server["cwd"]).is_absolute())
        self.assertTrue(server["args"][-1].replace("\\", "/").endswith("/server/stdio.py"))
        self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", json.dumps(config))
        self.assertIn("--strict-mcp-config", command)
        self.assertEqual(
            command[command.index("--prompt-suggestions") + 1],
            "false",
        )
        self.assertEqual(command[-1], "/onlyiflow:onlyiflow start a quick flow")

    def test_preflight_reports_missing_candidate_and_tools_without_model_calls(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            missing = Path(root) / "missing-candidate"
            with (
                patch(
                    "scripts.run_efficiency_measurements.CLAUDE_CANDIDATE",
                    missing,
                ),
                patch(
                    "scripts.run_efficiency_measurements.shutil.which",
                    return_value=None,
                ),
                patch(
                    "scripts.run_efficiency_measurements.cli_prefix",
                    side_effect=RuntimeError("Required CLI is unavailable: claude"),
                ),
                patch("scripts.run_efficiency_measurements.subprocess.run") as run,
            ):
                result = task5_preflight("claude")

        self.assertFalse(result["passed"])
        checks = {check["id"]: check for check in result["checks"]}
        self.assertFalse(checks["loader_candidate"]["passed"])
        self.assertFalse(checks["myself_runtime"]["passed"])
        self.assertFalse(checks["claude_cli"]["passed"])
        run.assert_not_called()

    def test_preflight_accepts_a_complete_claude_environment(self) -> None:
        conda_probe = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout='{"python":"3.12.0","fastmcp":"3.4.4"}\n',
            stderr="",
        )
        version_probe = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="2.1.212 (Claude Code)\n",
            stderr="",
        )
        validation = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Validation passed\n",
            stderr="",
        )
        with tempfile.TemporaryDirectory() as root:
            candidate = Path(root) / "onlyiflow"
            candidate.mkdir()
            with (
                patch(
                    "scripts.run_efficiency_measurements.CLAUDE_CANDIDATE",
                    candidate,
                ),
                patch(
                    "scripts.run_efficiency_measurements.shutil.which",
                    return_value="conda.exe",
                ),
                patch(
                    "scripts.run_efficiency_measurements.cli_prefix",
                    return_value=["claude.exe"],
                ),
                patch(
                    "scripts.run_efficiency_measurements.subprocess.run",
                    side_effect=[conda_probe, version_probe, validation],
                ),
            ):
                result = task5_preflight("claude")

        self.assertTrue(result["passed"])
        self.assertTrue(all(check["passed"] for check in result["checks"]))

    def test_task5_handoff_is_clone_relative_and_requires_preflight(self) -> None:
        handoff = (
            support.REPOSITORY_ROOT
            / "docs/evaluations/2026-07-17-task5-efficiency-and-gate-value.md"
        ).read_text(encoding="utf-8")

        self.assertNotIn("D:\\AgentX", handoff)
        self.assertNotIn("C:\\Users\\JS7B", handoff)
        self.assertIn("root of the current clone", handoff)
        self.assertIn("--host claude --preflight-only", handoff)
        self.assertIn("--host codex --preflight-only", handoff)
        self.assertIn(
            "Never run the two hosts concurrently",
            " ".join(handoff.split()),
        )

    def test_measurement_gate_catches_fault_then_passes_after_fix(self) -> None:
        from onlyiflow.runtime import Runtime

        with tempfile.TemporaryDirectory() as root:
            project = Path(root) / "project with spaces"
            prepare_project(project, "quick", managed=True)
            flow = Runtime().flow_start(str(project), "quick", "Gate fixture")
            self.assertTrue(flow["ok"])
            flow_id = flow["data"]["flow"]["id"]

            failed = Runtime().gate_run(str(project), flow_id)
            self.assertTrue(failed["ok"])
            self.assertFalse(failed["data"]["passed"])

            (project / "app.py").write_text(
                "def normalize_cache_key(value):\n"
                "    return str(value).strip().lower()\n",
                encoding="utf-8",
            )
            self.assertTrue(regression_passed(project))
            passed = Runtime().gate_run(str(project), flow_id)

            self.assertTrue(passed["ok"])
            self.assertTrue(passed["data"]["passed"])
            self.assertTrue(gate_evidence_is_private(project))


if __name__ == "__main__":
    unittest.main()
