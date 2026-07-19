from __future__ import annotations

import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RELEASE_GUIDE = REPOSITORY_ROOT / "docs/release-guide.md"
TASK7_EVIDENCE = (
    REPOSITORY_ROOT / "docs/evaluations/2026-07-17-task7-release-readiness.md"
)
V030_EVIDENCE = (
    REPOSITORY_ROOT / "docs/evaluations/2026-07-19-v0.3.0-gate-configuration.md"
)


class ReleaseDocumentationTests(unittest.TestCase):
    def test_v030_gate_configuration_is_documented_across_user_contracts(self) -> None:
        documents = [
            (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
            for relative_path in (
                "README.md",
                "README.zh-CN.md",
                "docs/product-spec.md",
                "docs/engineering-spec.md",
                "docs/release-guide.md",
            )
        ]

        for contents in documents:
            self.assertIn("0.3.0", contents)
            self.assertIn("gate_configure", contents)
        self.assertIn("eight deterministic MCP tools", documents[0])
        self.assertIn("八个确定性 MCP 工具", documents[1])
        self.assertIn("atomic replacement", documents[3])

    def test_release_guide_documents_each_verified_host_path(self) -> None:
        guide = RELEASE_GUIDE.read_text(encoding="utf-8")

        for expected in (
            "build/loader-candidates/codex-marketplace/",
            "build/loader-candidates/claude-marketplace/",
            "build/loader-candidates/zcode/",
            "$onlyiflow:onlyiflow",
            "/onlyiflow:onlyiflow",
            "plugin marketplace add",
            "claude plugin marketplace add",
            "claude plugin install onlyiflow@onlyiflow-local --scope user",
            "claude plugin disable onlyiflow@onlyiflow-local --scope user",
            "claude plugin enable onlyiflow@onlyiflow-local --scope user",
            "claude plugin uninstall onlyiflow@onlyiflow-local --scope user --yes",
            "scripts\\run_claude_user_install_lifecycle.py",
            "scripts\\run_claude_user_install_acceptance.py",
            "scripts\\run_release_smoke.py --host claude",
            "scripts\\run_release_smoke.py --host codex",
            "retained local Marketplace directory",
            "marketplace.json",
            '--output-root "<fresh-empty-output-root>"',
            "Use one launcher consistently within",
            "observed launcher versions belong in the evaluation evidence",
        ):
            self.assertIn(expected, guide)
        self.assertNotIn("--plugin-dir", guide)

        evidence = TASK7_EVIDENCE.read_text(encoding="utf-8")
        self.assertIn("working global npm Codex CLI 0.144.5", evidence)
        self.assertIn("Codex Desktop CLI 0.145.0-alpha.18", evidence)

    def test_v030_evidence_is_linked_and_records_deferred_host_checks(self) -> None:
        guide = RELEASE_GUIDE.read_text(encoding="utf-8")
        evidence = V030_EVIDENCE.read_text(encoding="utf-8")

        self.assertIn(V030_EVIDENCE.name, guide)
        self.assertIn("100/100", evidence)
        self.assertIn("12/12", evidence)
        self.assertIn("Codex live v0.3.0 verification: deferred by owner", evidence)
        self.assertIn("reports version 0.3.0 as installed", evidence)
        self.assertNotIn("existing Codex 0.2.0 plugin", evidence)
        self.assertIn("ZCode owner-assisted v0.3.0 smoke: passed", evidence)
        self.assertIn("build/v030-zcode-owner-smoke.json", evidence)

    def test_release_guide_freezes_prerequisites_and_enforcement_boundary(self) -> None:
        guide = RELEASE_GUIDE.read_text(encoding="utf-8")
        normalized = guide.casefold()

        for expected in (
            "python 3.11",
            "requirements.txt",
            "python -m pip install -r",
            "branch protection",
            "ci",
            "owner approval",
        ):
            self.assertIn(expected, normalized)
        for prohibited in ("myself", "conda run", "conda install", "npm install -g"):
            self.assertNotIn(prohibited, normalized)

    def test_release_verification_does_not_depend_on_the_old_repository(self) -> None:
        prohibited = ("D:" + "\\AgentX\\OnlyiFlow", "OnlyiFlow" + "_next")
        for directory in ("src", "server", "scripts", "tests"):
            for path in (REPOSITORY_ROOT / directory).rglob("*.py"):
                contents = path.read_text(encoding="utf-8")
                for value in prohibited:
                    self.assertNotIn(value, contents, path)

    def test_normative_documents_exclude_machine_and_task_history(self) -> None:
        for relative_path in (
            "README.md",
            "README.zh-CN.md",
            "docs/product-spec.md",
            "docs/engineering-spec.md",
            "docs/release-guide.md",
        ):
            contents = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
            self.assertNotIn("myself", contents.casefold(), relative_path)
            self.assertIsNone(re.search(r"[A-Z]:\\", contents), relative_path)
            self.assertIsNone(re.search(r"\bTask \d+\b", contents), relative_path)
            self.assertNotIn("At that checkpoint", contents, relative_path)

    def test_readmes_link_to_each_other(self) -> None:
        english = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        chinese = (REPOSITORY_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

        self.assertIn("[简体中文](README.zh-CN.md)", english)
        self.assertIn("[English](README.md)", chinese)

    def test_readmes_focus_on_capabilities_installation_and_execution(self) -> None:
        english = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        chinese = (REPOSITORY_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

        for expected in (
            "## Capabilities",
            "## Install And Start",
            "## Run A Workflow",
            "python -B scripts\\build_loader_candidates.py",
            "$onlyiflow:onlyiflow",
            "/onlyiflow:onlyiflow",
        ):
            self.assertIn(expected, english)
        for expected in ("## 核心能力", "## 安装与启动", "## 执行工作流"):
            self.assertIn(expected, chinese)

        for prohibited in (
            "does not install hooks",
            "environment-free",
            "remain out of scope",
            "cannot prevent",
        ):
            self.assertNotIn(prohibited, english.casefold())
        for prohibited in ("不会安装 hooks", "免环境方案", "仍不在范围内", "无法阻止"):
            self.assertNotIn(prohibited, chinese.casefold())

    def test_v030_is_the_documented_current_release(self) -> None:
        agents = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        english = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        chinese = (REPOSITORY_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
        evidence = V030_EVIDENCE.read_text(encoding="utf-8")

        self.assertIn("Version `0.3.0` is the current verified GitHub release", agents)
        self.assertIn("The current GitHub release is `v0.3.0`", english)
        self.assertIn("当前 GitHub 正式版本为 `v0.3.0`", chinese)
        self.assertIn("Status: released as v0.3.0", evidence)
        self.assertNotIn("The current GitHub release is `v0.1.0`", english)
        self.assertNotIn("当前 GitHub 正式版本为 `v0.1.0`", chinese)


if __name__ == "__main__":
    unittest.main()
