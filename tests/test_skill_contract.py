from __future__ import annotations

import json
import unittest
from pathlib import Path

import support


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CODEX_SKILL = REPOSITORY_ROOT / "skills/onlyiflow/SKILL.md"
CLAUDE_SKILL = REPOSITORY_ROOT / "skills-claude/onlyiflow/SKILL.md"
OPENAI_METADATA = REPOSITORY_ROOT / "skills/onlyiflow/agents/openai.yaml"
EVALUATIONS = REPOSITORY_ROOT / "tests/fixtures/skill_evaluations.json"
DESCRIPTION = (
    "Use only when the user explicitly invokes OnlyiFlow or explicitly asks to "
    "start, continue, check, or land an OnlyiFlow-managed flow. Manage explicit "
    "project-local workflow state with minimal risk-based ceremony and "
    "owner-controlled landing. Do not use for ordinary coding, planning, review, "
    "or generic workflow requests."
)
APPROVED_TOOLS = [
    "project_status",
    "project_init",
    "flow_start",
    "spec_submit",
    "flow_claim",
    "gate_run",
    "landing_request",
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
        self.assertIn('short_description: "Run an explicit, minimal development flow"', metadata)
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
            "changes must use the seven MCP tools.",
            "Never call `project_init` on the first unmanaged turn.",
            "Only call `project_init` after a new owner confirmation turn.",
            "Do not call `gate_run` unless the user explicitly asks to check or land.",
            "Call `landing_request` only after a passed gate.",
            "Report exactly one current state and one next action, then stop.",
            "For a managed quick start, call `project_status` and `flow_start` "
            "in the same turn.",
            "After a managed start reaches `implementing`, report the state and stop. "
            "Do not inspect or edit project files in that same explicit OnlyiFlow turn.",
            "Treat an intermediate `next_action` as transition guidance, not as "
            "a stop condition.",
            "Model uncertainty alone is not deep-risk evidence.",
            "Never create self-tracking TODOs, invoke another methodology Skill, spawn "
            "subagents, require a worktree, or add subjective review loops.",
        ]:
            self.assertIn(required, normalized)

        for tool in APPROVED_TOOLS:
            self.assertIn(f"`{tool}`", body)
        self.assertNotIn("workflow guidance is not implemented", body)

    def test_evaluation_set_has_the_approved_10_5_3_shape(self) -> None:
        evaluations = json.loads(EVALUATIONS.read_text(encoding="utf-8"))

        self.assertEqual(evaluations["description_revision_limit"], 1)
        self.assertLessEqual(
            evaluations["description_revision"],
            evaluations["description_revision_limit"],
        )
        self.assertEqual(len(evaluations["ordinary"]), 10)
        self.assertEqual(len(evaluations["explicit"]), 5)
        self.assertEqual(len(evaluations["deep"]), 3)

        ids = [
            case["id"]
            for group in ["ordinary", "explicit", "deep"]
            for case in evaluations[group]
        ]
        self.assertEqual(len(ids), len(set(ids)))

        for case in evaluations["ordinary"]:
            self.assertNotIn("onlyiflow", case["prompt"].casefold())
            self.assertIs(case["activate"], False)
            self.assertEqual(case["onlyiflow_calls"], 0)

        for case in evaluations["explicit"]:
            self.assertTrue(
                case["codex_prompt"].startswith("$onlyiflow:onlyiflow ")
            )
            self.assertTrue(
                case["claude_prompt"].startswith("/onlyiflow:onlyiflow ")
            )
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
