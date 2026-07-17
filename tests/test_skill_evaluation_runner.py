from __future__ import annotations

import json
import tempfile
import sys
import unittest
from pathlib import Path

import support

from scripts.run_skill_evaluations import (
    CLAUDE_TOOLS,
    TOOLS,
    ProcessResult,
    assistant_excerpt,
    assistant_output,
    called_tools,
    claude_command,
    cli_prefix,
    codex_command,
    codex_skill_prompt,
    evaluate_case,
    event_types,
    prepare_project,
    run_process,
)


class SkillEvaluationRunnerTests(unittest.TestCase):
    def test_event_types_are_compact_and_content_free(self) -> None:
        output = "\n".join(
            [
                '{"type":"thread.started","thread_id":"secret"}',
                (
                    '{"type":"item.completed","item":{"type":"mcp_tool_call",'
                    '"server":"onlyiflow","tool":"project_status",'
                    '"arguments":{"project_root":"C:/secret"}}}'
                ),
            ]
        )

        self.assertEqual(
            event_types(output),
            ["item.completed", "mcp_tool_call", "thread.started"],
        )

    def test_project_setups_create_the_expected_preconditions(self) -> None:
        expected = {
            "unmanaged": (False, None, 0, 0),
            "managed": (True, None, 0, 0),
            "ready": (True, "ready", 1, 0),
            "implementing_with_gate": (True, "implementing", 0, 0),
        }
        for setup, values in expected.items():
            with self.subTest(setup=setup):
                with tempfile.TemporaryDirectory() as root:
                    project = Path(root) / setup
                    snapshot = prepare_project(project, setup)
                state = (
                    snapshot["flows"][-1]["state"]
                    if snapshot["flows"]
                    else None
                )
                self.assertEqual(
                    (
                        snapshot["managed"],
                        state,
                        snapshot["specs"],
                        snapshot["gate_runs"],
                    ),
                    values,
                )

    def test_enabled_quick_case_requires_the_expected_database_state(self) -> None:
        case = {
            "expected_state": "implementing",
            "expected_specs": 0,
            "expected_gate_runs": 0,
            "expected_tools": ["project_status", "flow_start"],
        }
        before = {
            "managed": True,
            "flows": [],
            "specs": 0,
            "gate_runs": 0,
            "events": 0,
        }
        after = {
            "managed": True,
            "flows": [{"risk": "quick", "state": "implementing"}],
            "specs": 0,
            "gate_runs": 0,
            "events": 1,
        }

        status, reasons, _ = evaluate_case(
            group="explicit",
            case=case,
            enabled=True,
            before=before,
            after=after,
            process=self.success_with_tools("project_status", "flow_start"),
        )

        self.assertEqual(status, "passed")
        self.assertEqual(reasons, [])

    def test_enabled_explicit_case_rejects_state_mutation_without_mcp_calls(self) -> None:
        case = {
            "expected_state": "implementing",
            "expected_specs": 0,
            "expected_gate_runs": 0,
            "expected_tools": ["project_status", "flow_start"],
        }
        before = {
            "managed": True,
            "flows": [],
            "specs": 0,
            "gate_runs": 0,
            "events": 0,
        }
        after = {
            "managed": True,
            "flows": [{"risk": "quick", "state": "implementing"}],
            "specs": 0,
            "gate_runs": 0,
            "events": 1,
        }

        status, reasons, _ = evaluate_case(
            group="explicit",
            case=case,
            enabled=True,
            before=before,
            after=after,
            process=self.success(),
        )

        self.assertEqual(status, "failed")
        self.assertEqual(reasons, ["unexpected_onlyiflow_tool_sequence"])

    def test_deep_case_requires_status_confirmation_and_zero_mutation(self) -> None:
        snapshot = {
            "managed": True,
            "flows": [],
            "specs": 0,
            "gate_runs": 0,
            "events": 0,
        }
        process = ProcessResult(
            returncode=0,
            stdout="\n".join(
                [
                    (
                        '{"type":"tool_use","name":'
                        '"mcp__plugin_onlyiflow_onlyiflow__project_status"}'
                    ),
                    (
                        '{"type":"item.completed","item":{"type":"agent_message",'
                        '"text":"This is deep because authentication is '
                        'security-sensitive. Please confirm before continuing."}}'
                    ),
                ]
            ),
            stderr="",
            duration_seconds=1.0,
        )

        status, reasons, _ = evaluate_case(
            group="deep",
            case={},
            enabled=True,
            before=snapshot,
            after=snapshot,
            process=process,
        )

        self.assertEqual(status, "passed")
        self.assertEqual(reasons, [])

    def test_timeout_is_infrastructure_not_behavior_failure(self) -> None:
        snapshot = {
            "managed": False,
            "flows": [],
            "specs": 0,
            "gate_runs": 0,
            "events": 0,
        }

        status, reasons, _ = evaluate_case(
            group="ordinary",
            case={},
            enabled=True,
            before=snapshot,
            after=snapshot,
            process=ProcessResult(
                returncode=None,
                stdout="",
                stderr="",
                duration_seconds=180.0,
                timed_out=True,
            ),
        )

        self.assertEqual(status, "infrastructure_error")
        self.assertEqual(reasons, ["host_model_or_network_unavailable"])

    def test_enabled_host_without_project_status_is_infrastructure_failure(self) -> None:
        snapshot = {
            "managed": True,
            "flows": [],
            "specs": 0,
            "gate_runs": 0,
            "events": 0,
        }
        process = ProcessResult(
            returncode=0,
            stdout=(
                '{"type":"item.completed","item":{"type":"agent_message",'
                '"text":"The project_status MCP tool is not exposed in this session."}}'
            ),
            stderr="",
            duration_seconds=1.0,
        )

        status, reasons, _ = evaluate_case(
            group="explicit",
            case={
                "expected_state": "implementing",
                "expected_specs": 0,
                "expected_gate_runs": 0,
                "expected_tools": ["project_status", "flow_start"],
            },
            enabled=True,
            before=snapshot,
            after=snapshot,
            process=process,
        )

        self.assertEqual(status, "infrastructure_error")
        self.assertEqual(reasons, ["enabled_host_tools_unavailable"])

    def test_only_actual_tool_use_events_count_as_calls(self) -> None:
        output = "\n".join(
            [
                '{"type":"system","tools":["project_status","flow_start"]}',
                (
                    '{"type":"assistant","message":{"role":"assistant","content":['
                    '{"type":"tool_use","name":'
                    '"mcp__plugin_onlyiflow_onlyiflow__project_status"}]}}'
                ),
                (
                    '{"type":"item.completed","item":{"type":"mcp_tool_call",'
                    '"tool":"gate_run"}}'
                ),
                (
                    '{"type":"item.completed","item":{"type":"mcp_tool_call",'
                    '"tool":"project_status"}}'
                ),
            ]
        )

        self.assertEqual(
            called_tools(output),
            ["project_status", "gate_run", "project_status"],
        )

    def test_codex_started_and_completed_events_count_one_call(self) -> None:
        item = {
            "type": "mcp_tool_call",
            "id": "call-1",
            "server": "onlyiflow",
            "tool": "project_status",
        }
        output = "\n".join(
            json.dumps({"type": event_type, "item": item})
            for event_type in ["item.started", "item.completed"]
        )

        self.assertEqual(called_tools(output), ["project_status"])

    def test_assistant_output_excludes_system_and_user_text(self) -> None:
        output = "\n".join(
            [
                '{"type":"system","message":"deep confirm"}',
                '{"type":"user","message":{"role":"user","content":"deep confirm"}}',
                (
                    '{"type":"assistant","message":{"role":"assistant","content":['
                    '{"type":"text","text":"Please confirm deep."}]}}'
                ),
                (
                    '{"type":"item.completed","item":{"type":"agent_message",'
                    '"text":"OnlyiFlow state is managed."}}'
                ),
            ]
        )

        self.assertEqual(
            assistant_output(output),
            "Please confirm deep.\nOnlyiFlow state is managed.",
        )

    def test_assistant_excerpt_is_compact_and_hides_absolute_paths(self) -> None:
        output = (
            '{"type":"item.completed","item":{"type":"agent_message",'
            '"text":"State at C:/Users/example/project is managed.\\nNext action."}}'
        )

        excerpt = assistant_excerpt(output)

        self.assertEqual(excerpt, "State at <path> is managed. Next action.")

    def test_run_process_marks_timeout_and_terminates(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            result = run_process(
                [
                    sys.executable,
                    "-c",
                    "import time; time.sleep(5)",
                ],
                cwd=Path(root),
                timeout_seconds=1,
            )

        self.assertTrue(result.timed_out)
        self.assertIsNone(result.returncode)

    def test_run_process_closes_standard_input(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            result = run_process(
                [
                    sys.executable,
                    "-c",
                    "import sys; print(repr(sys.stdin.read()))",
                ],
                cwd=Path(root),
                timeout_seconds=30,
            )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "''")

    def test_run_process_allows_slow_mcp_startup(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            result = run_process(
                [
                    sys.executable,
                    "-c",
                    "import os; print(os.environ.get('MCP_TIMEOUT'))",
                ],
                cwd=Path(root),
                timeout_seconds=30,
            )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "60000")

    def test_host_commands_use_fresh_nonpersistent_sessions(self) -> None:
        project = Path("project")
        codex_enabled = codex_command(project, "prompt", enabled=True)
        codex_disabled = codex_command(project, "prompt", enabled=False)
        claude_enabled = claude_command(project, "prompt", enabled=True)
        claude_disabled = claude_command(project, "prompt", enabled=False)

        self.assertIn("--ephemeral", codex_enabled)
        self.assertIn("--skip-git-repo-check", codex_enabled)
        self.assertIn('model_reasoning_effort="low"', codex_enabled)
        self.assertEqual(
            codex_enabled[codex_enabled.index("-s") + 1],
            "workspace-write",
        )
        self.assertEqual(
            codex_disabled[codex_disabled.index("-s") + 1],
            "read-only",
        )
        codex_enabled_config = [
            codex_enabled[index + 1]
            for index, value in enumerate(codex_enabled)
            if value == "-c"
        ]
        self.assertIn(
            "plugins.onlyiflow.mcp_servers.onlyiflow.enabled=true",
            codex_enabled_config,
        )
        self.assertIn(
            'plugins.onlyiflow.mcp_servers.onlyiflow.'
            'default_tools_approval_mode="approve"',
            codex_enabled_config,
        )
        self.assertIn(
            "plugins.onlyiflow.mcp_servers.onlyiflow.enabled_tools="
            + json.dumps(list(TOOLS), separators=(",", ":")),
            codex_enabled_config,
        )
        self.assertNotIn(
            "plugins.onlyiflow.mcp_servers",
            " ".join(codex_disabled),
        )
        self.assertIn("--no-session-persistence", claude_enabled)
        self.assertIn("--effort", claude_enabled)
        self.assertIn("low", claude_enabled)
        self.assertIn("--plugin-dir", claude_enabled)
        self.assertIn("--allowedTools", claude_enabled)
        allowed = claude_enabled[claude_enabled.index("--allowedTools") + 1]
        self.assertEqual(allowed.split(","), list(CLAUDE_TOOLS))
        self.assertIn("--disable-slash-commands", claude_disabled)

    def test_windows_cli_prefixes_are_directly_executable(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            for name in ["codex", "claude"]:
                with self.subTest(name=name):
                    prefix = cli_prefix(name)
                    self.assertNotIn(
                        Path(prefix[0]).suffix.casefold(),
                        {".cmd", ".bat", ".ps1"},
                    )
                    result = run_process(
                        [*prefix, "--version"],
                        cwd=Path(root),
                        timeout_seconds=30,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(result.timed_out)

    def test_codex_explicit_prompt_uses_the_installed_skill_link(self) -> None:
        prompt = codex_skill_prompt(
            "$onlyiflow:onlyiflow start a quick flow.",
            Path("C:/cache/onlyiflow/SKILL.md"),
        )

        self.assertEqual(
            prompt,
            "[$onlyiflow:onlyiflow](C:/cache/onlyiflow/SKILL.md) "
            "start a quick flow.",
        )

    def success(self) -> ProcessResult:
        return ProcessResult(
            returncode=0,
            stdout="",
            stderr="",
            duration_seconds=1.0,
        )

    def success_with_tools(self, *tools: str) -> ProcessResult:
        return ProcessResult(
            returncode=0,
            stdout="\n".join(
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "mcp_tool_call",
                            "server": "onlyiflow",
                            "tool": tool,
                        },
                    }
                )
                for tool in tools
            ),
            stderr="",
            duration_seconds=1.0,
        )


if __name__ == "__main__":
    unittest.main()
