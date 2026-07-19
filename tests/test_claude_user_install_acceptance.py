from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.run_claude_user_install_acceptance import evaluate_model_case
from scripts.run_skill_evaluations import ProcessResult


class ClaudeUserInstallAcceptanceTests(unittest.TestCase):
    def test_unmanaged_explicit_case_requires_status_and_confirmation(self) -> None:
        process = self.result(
            self.tool_event("project_status"),
            self.assistant_event("The project is unmanaged. Confirm initialization."),
        )

        status, reasons, evidence = evaluate_model_case(
            process=process,
            expected_tools=["project_status"],
            before={"managed": False},
            after={"managed": False},
            expected_after={"managed": False},
            require_confirmation=True,
        )

        self.assertEqual(status, "passed")
        self.assertEqual(reasons, [])
        self.assertEqual(evidence["tool_mentions"], ["project_status"])
        self.assertNotIn("assistant_excerpt", evidence)

    def test_ordinary_case_passes_only_with_zero_calls_and_zero_mutation(self) -> None:
        process = self.result(self.assistant_event("Version 0.3.0."))

        status, reasons, evidence = evaluate_model_case(
            process=process,
            expected_tools=[],
            before={"managed": False, "source_unchanged": True},
            after={"managed": False, "source_unchanged": True},
            expected_after={"managed": False, "source_unchanged": True},
        )

        self.assertEqual(status, "passed")
        self.assertEqual(reasons, [])
        self.assertEqual(evidence["tool_mentions"], [])

    def test_gate_proposal_requires_the_owner_visible_check_details(self) -> None:
        incomplete = self.result(
            self.tool_event("project_status"),
            self.assistant_event("Please confirm the Gate."),
        )

        status, reasons, _ = evaluate_model_case(
            process=incomplete,
            expected_tools=["project_status"],
            before={"gate_config": {"configured": False}},
            after={"gate_config": {"configured": False}},
            expected_after={"gate_config": {"configured": False}},
            require_confirmation=True,
            required_response_terms=["tests", "python", "120"],
        )

        self.assertEqual(status, "failed")
        self.assertEqual(reasons, ["gate_proposal_details_missing"])

        complete = self.result(
            self.tool_event("project_status"),
            self.assistant_event(
                "Confirm required check tests: python -m unittest, timeout 120 seconds."
            ),
        )
        status, reasons, _ = evaluate_model_case(
            process=complete,
            expected_tools=["project_status"],
            before={"gate_config": {"configured": False}},
            after={"gate_config": {"configured": False}},
            expected_after={"gate_config": {"configured": False}},
            require_confirmation=True,
            required_response_terms=["tests", "python", "120"],
        )
        self.assertEqual(status, "passed")
        self.assertEqual(reasons, [])

    def test_unexpected_call_and_state_are_both_reported(self) -> None:
        process = self.result(
            self.tool_event("project_status"),
            self.tool_event("project_init"),
        )

        status, reasons, _ = evaluate_model_case(
            process=process,
            expected_tools=["project_status"],
            before={"managed": False},
            after={"managed": True},
            expected_after={"managed": False},
            require_confirmation=True,
        )

        self.assertEqual(status, "failed")
        self.assertEqual(
            reasons,
            [
                "unexpected_onlyiflow_tool_sequence",
                "unexpected_project_state",
                "owner_confirmation_not_requested",
            ],
        )

    def test_failed_host_session_records_a_bounded_redacted_stderr_excerpt(
        self,
    ) -> None:
        home = str(Path.home())
        process = ProcessResult(
            returncode=1,
            stdout="",
            stderr=f"Plugin cache unavailable at {home}\\.claude\\plugins\\cache",
            duration_seconds=1.0,
        )

        status, reasons, evidence = evaluate_model_case(
            process=process,
            expected_tools=["project_status"],
            before={"managed": False},
            after={"managed": False},
            expected_after={"managed": False},
        )

        self.assertEqual(status, "failed")
        self.assertEqual(reasons, ["installed_host_session_failed"])
        self.assertIn("<home>", evidence["host_stderr_excerpt"])
        self.assertNotIn(home, evidence["host_stderr_excerpt"])
        self.assertLessEqual(len(evidence["host_stderr_excerpt"]), 1000)

    def test_failed_behavior_records_a_bounded_assistant_excerpt(self) -> None:
        process = self.result(self.assistant_event("Unknown OnlyiFlow skill."))

        status, _, evidence = evaluate_model_case(
            process=process,
            expected_tools=["project_status"],
            before={"managed": False},
            after={"managed": False},
            expected_after={"managed": False},
        )

        self.assertEqual(status, "failed")
        self.assertEqual(evidence["assistant_excerpt"], "Unknown OnlyiFlow skill.")

    def test_missing_installed_tools_in_chinese_is_infrastructure_error(self) -> None:
        process = self.result(
            self.assistant_event(
                "OnlyiFlow 的八个 MCP 工具没有出现在工具列表中，project_status 不可用。"
            )
        )

        status, reasons, _ = evaluate_model_case(
            process=process,
            expected_tools=["project_status", "flow_start"],
            before={"managed": True},
            after={"managed": True},
            expected_after={"managed": True, "flows": ["implementing"]},
        )

        self.assertEqual(status, "infrastructure_error")
        self.assertEqual(reasons, ["installed_host_tools_unavailable"])

    def result(self, *events: str) -> ProcessResult:
        return ProcessResult(
            returncode=0,
            stdout="\n".join(events),
            stderr="",
            duration_seconds=1.0,
        )

    def tool_event(self, tool: str) -> str:
        return json.dumps(
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "name": f"mcp__plugin_onlyiflow_onlyiflow__{tool}",
                        }
                    ],
                },
            }
        )

    def assistant_event(self, text: str) -> str:
        return json.dumps(
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": text}],
                },
            }
        )


if __name__ == "__main__":
    unittest.main()
