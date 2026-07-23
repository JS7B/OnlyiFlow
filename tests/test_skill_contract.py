from __future__ import annotations

import json
import unittest
from pathlib import Path

import support  # noqa: F401  # Adds the repository source root to sys.path.


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CODEX_SKILL = REPOSITORY_ROOT / "packaging/codex/skills/onlyiflow/SKILL.md"
CLAUDE_SKILL = REPOSITORY_ROOT / "packaging/shared/skills-claude/onlyiflow/SKILL.md"
CODEX_WAVE_REFERENCE = (
    REPOSITORY_ROOT / "packaging/codex/skills/onlyiflow/references/wave-workflow.md"
)
CLAUDE_WAVE_REFERENCE = (
    REPOSITORY_ROOT
    / "packaging/shared/skills-claude/onlyiflow/references/wave-workflow.md"
)
OPENAI_METADATA = (
    REPOSITORY_ROOT / "packaging/codex/skills/onlyiflow/agents/openai.yaml"
)
EVALUATIONS = REPOSITORY_ROOT / "tests/fixtures/skill_evaluations.json"
DESCRIPTION = (
    "Use only when the user explicitly invokes OnlyiFlow or explicitly asks to "
    "start, continue, check, land, or close an OnlyiFlow-managed flow. Manage explicit "
    "project-local workflow state with minimal risk-based ceremony and "
    "owner-controlled landing. Do not use for ordinary coding, planning, review, "
    "or generic workflow requests."
)
APPROVED_TOOLS = [
    "project_status",
    "project_init",
    "gate_configure",
    "flow_start",
    "spec_submit",
    "wave_plan_set",
    "flow_claim",
    "work_package_status",
    "work_package_record",
    "gate_run",
    "landing_request",
    "flow_close",
]


class SkillContractTests(unittest.TestCase):
    def test_host_frontmatter_is_manual_only_and_body_is_portable(self) -> None:
        codex_frontmatter, codex_body = self.read_skill(CODEX_SKILL)
        claude_frontmatter, claude_body = self.read_skill(CLAUDE_SKILL)

        self.assertEqual(
            codex_frontmatter,
            {
                "name": "onlyiflow",
                "description": DESCRIPTION,
            },
        )
        self.assertEqual(
            claude_frontmatter,
            {
                "name": "onlyiflow",
                "description": DESCRIPTION,
                "disable-model-invocation": "true",
            },
        )
        self.assertEqual(codex_body, claude_body)

        metadata = OPENAI_METADATA.read_text(encoding="utf-8")
        self.assertIn('display_name: "OnlyiFlow"', metadata)
        self.assertIn(
            'short_description: "Run an explicit, minimal development flow"', metadata
        )
        self.assertIn(
            'default_prompt: "Use $onlyiflow:onlyiflow to start or resume an explicit '
            'workflow for the current project."',
            metadata,
        )
        self.assertIn("allow_implicit_invocation: false", metadata)
        self.assertNotIn("foundation", metadata.casefold())

    def test_skill_encodes_the_required_stop_and_transition_boundaries(self) -> None:
        _, body = self.read_skill(CODEX_SKILL)
        normalized = " ".join(body.split())

        for required in [
            "Call `project_status` exactly once at the start.",
            "Pass the host's absolute current working directory to `project_status` exactly "
            "as provided; do not translate it to another path syntax or retry with a "
            "second path.",
            "Do not probe or list MCP servers.",
            "If `project_status` is absent from the initial tool list, do not report it "
            "unavailable.",
            "Use the host's native tool search exactly once for the literal query "
            "`project_status`, then invoke the returned tool.",
            "Never inspect or modify `.onlyiflow` directly; all workflow state reads and "
            "changes must use the twelve MCP tools.",
            "Never call `project_init` on the first unmanaged turn.",
            "Only call `project_init` after a new owner confirmation turn.",
            "Never call `gate_configure` before a new owner confirmation turn.",
            "Gate is the project's fixed final quality check set. It runs only when the "
            "owner explicitly asks to `check` or `land`; configuration stores the complete "
            "list and does not run commands, install dependencies, review code, or perform "
            "Git operations.",
            "Present the proposed check IDs, required flags, commands, and timeouts, then "
            "stop for owner confirmation.",
            "After confirmation, call `gate_configure` once and follow its returned next "
            "action. For a project with no active flow, report that the Gate is ready "
            "and make `flow_start` the one next action.",
            "For an unconfigured legacy active flow, resume the returned active-flow "
            "action. Never replace a configured Gate while a flow is active.",
            "Do not call `gate_run` unless the user explicitly asks to check or land and "
            "all Wave packages are complete.",
            "For a direct flow, an explicit `check` is complete owner authorization to "
            "call `gate_run`. When `project_status` returns an `implementing` direct flow, "
            "call `gate_run` in the same turn. Do not report, stop, ask a question, or "
            "request confirmation between these calls.",
            "Call `landing_request` only after a passed gate.",
            "Before calling `flow_close`, present the Flow ID, current state, requested "
            "terminal result, and reason code, then stop for a separate owner confirmation "
            "turn.",
            "Call `flow_close` only after that confirmation. It records an already completed "
            "owner decision and never runs Git, merges, pushes, or publishes.",
            "Use `landed` with `external_landing_completed` only from `waiting_owner`. Use "
            "`abandoned` from any nonterminal state with exactly one of `owner_cancelled`, "
            "`goal_invalidated`, `scope_drifted`, or `goal_superseded`.",
            "A closed Flow releases the active slot, so start the next Flow without deleting "
            "`.onlyiflow`; the closed Flow and its history remain retained.",
            "Report exactly one current state and one next action, then stop.",
            "For a managed quick start, call `project_status` and `flow_start` "
            "in the same turn.",
            "After a managed start reaches `implementing`, report the state and stop. "
            "Do not inspect or edit project files in that same explicit OnlyiFlow turn.",
            "Treat an intermediate `next_action` as transition guidance, not as "
            "a stop condition.",
            "Model uncertainty alone is not deep-risk evidence.",
            "Outside confirmed Wave mode, never create self-tracking TODOs, invoke "
            "another methodology Skill, spawn subagents, require a worktree, or add "
            "subjective review loops.",
        ]:
            self.assertIn(required, normalized)

        for tool in APPROVED_TOOLS[:6] + APPROVED_TOOLS[-2:]:
            self.assertIn(f"`{tool}`", body)
        wave_reference = CODEX_WAVE_REFERENCE.read_text(encoding="utf-8")
        for tool in ["wave_plan_set", "work_package_status", "work_package_record"]:
            self.assertIn(f"`{tool}`", body + wave_reference)
        self.assertNotIn("workflow guidance is not implemented", body)

    def test_wave_guidance_is_explicit_progressive_and_host_owned(self) -> None:
        _, body = self.read_skill(CODEX_SKILL)
        codex_reference = CODEX_WAVE_REFERENCE.read_text(encoding="utf-8")
        claude_reference = CLAUDE_WAVE_REFERENCE.read_text(encoding="utf-8")

        self.assertEqual(codex_reference, claude_reference)
        self.assertLessEqual(len(body.splitlines()), 180)
        self.assertLessEqual(len(codex_reference.splitlines()), 260)
        normalized = " ".join(body.split())
        self.assertIn(
            "Only after the owner explicitly selects or confirms Wave mode, read "
            "`references/wave-workflow.md` once.",
            normalized,
        )
        self.assertIn(
            "`mode=wave` requires `risk=standard` or `risk=deep`; `risk=quick` is "
            "invalid.",
            normalized,
        )
        self.assertIn("present the complete Wave plan and stop", normalized)
        self.assertIn("a new owner confirmation turn", normalized)

        normalized_reference = " ".join(codex_reference.split())
        for required in [
            "The host decides whether to use native subagents or worktrees.",
            "OnlyiFlow never creates, assigns, interrupts, or removes them.",
            "One Flow is one Goal; work packages are children, not additional active flows.",
            "Only `integrated` packages satisfy dependencies.",
            "Plan confirmation does not authorize dependency installation, external writes, "
            "destructive actions, Git operations, or release.",
            "Use `work_package_status` to load only the target package.",
            "Use `work_package_record` only after the host action it records has occurred.",
            "Do not create self-tracking TODOs or reflection logs.",
            "Do not require an independent reviewer unless the package contract requires one.",
            "Material scope, dependency, acceptance, authority, or Wave changes require a "
            "separately confirmed replan.",
            "Standard and deep flows may use Wave mode; quick flows may not.",
            "A standard Wave still requires explicit selection or confirmation of Wave mode "
            "and a separate confirmation of the complete plan.",
        ]:
            self.assertIn(required, normalized_reference)

        for prohibited in [
            "OnlyiFlow spawns",
            "OnlyiFlow creates a worktree",
            "OnlyiFlow merges",
            "automatic reviewer",
        ]:
            self.assertNotIn(prohibited.casefold(), codex_reference.casefold())

    def test_evaluation_set_preserves_10_5_3_and_adds_bounded_wave_cases(self) -> None:
        evaluations = json.loads(EVALUATIONS.read_text(encoding="utf-8"))

        self.assertEqual(evaluations["description_revision_limit"], 1)
        self.assertLessEqual(
            evaluations["description_revision"],
            evaluations["description_revision_limit"],
        )
        self.assertEqual(len(evaluations["ordinary"]), 10)
        self.assertEqual(len(evaluations["explicit"]), 5)
        self.assertEqual(len(evaluations["deep"]), 3)
        self.assertEqual(len(evaluations["wave"]), 3)

        ids = [
            case["id"]
            for group in ["ordinary", "explicit", "deep", "wave"]
            for case in evaluations[group]
        ]
        self.assertEqual(len(ids), len(set(ids)))

        for case in evaluations["ordinary"]:
            self.assertNotIn("onlyiflow", case["prompt"].casefold())
            self.assertIs(case["activate"], False)
            self.assertEqual(case["onlyiflow_calls"], 0)

        for case in evaluations["explicit"]:
            self.assertTrue(case["codex_prompt"].startswith("$onlyiflow:onlyiflow "))
            self.assertTrue(case["claude_prompt"].startswith("/onlyiflow:onlyiflow "))
            self.assertIs(case["activate"], True)
            self.assertIn(
                case["setup"],
                {"managed", "ready", "implementing_with_gate"},
            )
            self.assertIn(
                case["expected_state"],
                {"implementing", "gate_passed", "waiting_owner"},
            )
            self.assertGreaterEqual(case["expected_specs"], 0)
            self.assertGreaterEqual(case["expected_gate_runs"], 0)
            self.assertTrue(case["expected_tools"])
            self.assertEqual(case["expected_tools"][0], "project_status")
            self.assertEqual(
                len(case["expected_tools"]),
                len(set(case["expected_tools"])),
            )
            self.assertLessEqual(set(case["expected_tools"]), set(APPROVED_TOOLS))

        for case in evaluations["deep"]:
            self.assertTrue(case["objective_evidence"])
            self.assertEqual(case["setup"], "managed")
            self.assertEqual(case["expected_risk"], "deep")
            self.assertIs(case["requires_owner_confirmation"], True)

        expected_wave_tools = {
            "proposal": ["project_status"],
            "confirmation": [
                "project_status",
                "spec_submit",
                "wave_plan_set",
                "flow_claim",
            ],
            "incomplete_check": ["project_status"],
        }
        for case in evaluations["wave"]:
            self.assertTrue(case["codex_prompt"].startswith("$onlyiflow:onlyiflow "))
            self.assertTrue(case["claude_prompt"].startswith("/onlyiflow:onlyiflow "))
            self.assertEqual(case["expected_tools"], expected_wave_tools[case["phase"]])
            self.assertEqual(case["expected_gate_runs"], 0)
            self.assertLessEqual(set(case["expected_tools"]), set(APPROVED_TOOLS))

    def test_direct_state_routing_cannot_override_wave_guards(self) -> None:
        _, body = self.read_skill(CODEX_SKILL)
        normalized = " ".join(body.split())

        self.assertIn(
            "The state rules below apply only to `mode=direct`; they never route a Wave "
            "`draft` through the direct spec-and-claim sequence or route an incomplete "
            "Wave to `gate_run`.",
            normalized,
        )
        self.assertNotIn("- `draft`: for `start` or `continue`", normalized)
        self.assertNotIn(
            "For `check` or `land` while `implementing`, call `gate_run`.",
            normalized,
        )

    def read_skill(self, path: Path) -> tuple[dict[str, str], str]:
        text = path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        _, raw_frontmatter, body = text.split("---", 2)
        frontmatter = {}
        for line in raw_frontmatter.strip().splitlines():
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()
        return frontmatter, body.strip()


if __name__ == "__main__":
    unittest.main()
