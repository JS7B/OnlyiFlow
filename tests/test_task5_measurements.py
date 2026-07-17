from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import support

from scripts.run_efficiency_measurements import (
    APPROVED_METRIC_KEYS,
    build_report,
    evaluate_budgets,
    gate_evidence_is_private,
    prepare_project,
    regression_passed,
    source_snapshot,
    summarize_flow,
    task5_host_command,
)


class Task5MeasurementTests(unittest.TestCase):
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
        self.assertEqual(command[-1], "ordinary prompt")

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
