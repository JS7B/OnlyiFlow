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
V040_CANDIDATE_EVIDENCE = (
    REPOSITORY_ROOT / "docs/evaluations/2026-07-20-post-v030-wave-development.md"
)
LOCAL_CONTRACTS_AVAILABLE = all(
    path.is_file()
    for path in (
        REPOSITORY_ROOT / "AGENTS.md",
        REPOSITORY_ROOT / "docs/product-spec.md",
        REPOSITORY_ROOT / "docs/engineering-spec.md",
        RELEASE_GUIDE,
        TASK7_EVIDENCE,
        V030_EVIDENCE,
        V040_CANDIDATE_EVIDENCE,
    )
)


class ReleaseDocumentationTests(unittest.TestCase):
    @unittest.skipUnless(
        LOCAL_CONTRACTS_AVAILABLE,
        "local normative contracts are not part of the public repository",
    )
    def test_v030_gate_configuration_is_documented_across_user_contracts(self) -> None:
        documents = [
            (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
            for relative_path in (
                "README.md",
                "docs/product-spec.md",
                "docs/engineering-spec.md",
                "docs/release-guide.md",
            )
        ]

        for contents in documents:
            self.assertIn("0.5.0", contents)
            self.assertIn("gate_configure", contents)
        self.assertIn("十二个确定性 MCP 工具", documents[0])
        self.assertIn("atomic replacement", documents[2])

    @unittest.skipUnless(
        LOCAL_CONTRACTS_AVAILABLE,
        "local normative contracts are not part of the public repository",
    )
    def test_wave_development_contract_is_documented_without_host_takeover(
        self,
    ) -> None:
        documents = [
            (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
            for relative_path in (
                "README.md",
                "docs/product-spec.md",
                "docs/engineering-spec.md",
            )
        ]

        for contents in documents:
            for tool in (
                "wave_plan_set",
                "work_package_status",
                "work_package_record",
            ):
                self.assertIn(tool, contents)
        self.assertIn("由宿主决定", documents[0])
        self.assertIn(
            "Direct quick and standard call sequences remain unchanged", documents[1]
        )
        self.assertIn("twelve tool registrations", documents[2])
        self.assertIn(
            "$onlyiflow:onlyiflow 为这个迁移目标启动 deep Wave 流程",
            documents[0],
        )

        guide = RELEASE_GUIDE.read_text(encoding="utf-8")
        normalized_guide = " ".join(guide.split())
        self.assertIn(
            "before persisting either the compact spec or the package plan",
            normalized_guide,
        )
        self.assertIn(
            "Only a later owner turn may call `spec_submit`, record the complete plan "
            "with `wave_plan_set`, and claim the Flow, in that order.",
            normalized_guide,
        )
        self.assertNotIn("plan-confirmation boundary after its compact spec", guide)

    @unittest.skipUnless(
        LOCAL_CONTRACTS_AVAILABLE,
        "local normative contracts are not part of the public repository",
    )
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

    @unittest.skipUnless(
        LOCAL_CONTRACTS_AVAILABLE,
        "local normative contracts are not part of the public repository",
    )
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

    @unittest.skipUnless(
        LOCAL_CONTRACTS_AVAILABLE,
        "local normative contracts are not part of the public repository",
    )
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

    @unittest.skipUnless(
        LOCAL_CONTRACTS_AVAILABLE,
        "local normative contracts are not part of the public repository",
    )
    def test_normative_documents_exclude_machine_and_task_history(self) -> None:
        for relative_path in (
            "README.md",
            "docs/product-spec.md",
            "docs/engineering-spec.md",
            "docs/release-guide.md",
        ):
            contents = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
            self.assertNotIn("myself", contents.casefold(), relative_path)
            self.assertIsNone(re.search(r"[A-Z]:\\", contents), relative_path)
            self.assertIsNone(re.search(r"\bTask \d+\b", contents), relative_path)
            self.assertNotIn("At that checkpoint", contents, relative_path)

    def test_repository_has_one_chinese_readme(self) -> None:
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertFalse((REPOSITORY_ROOT / "README.zh-CN.md").exists())
        self.assertIn("## 核心能力", readme)
        self.assertNotIn("[简体中文]", readme)
        self.assertNotIn("[English]", readme)

    def test_readme_focuses_on_capabilities_installation_and_execution(self) -> None:
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")

        for expected in (
            "## 核心能力",
            "## 安装与启动",
            "## 执行工作流",
            "python -B scripts\\build_loader_candidates.py",
            "$onlyiflow:onlyiflow",
            "/onlyiflow:onlyiflow",
        ):
            self.assertIn(expected, readme)

        for prohibited in ("不会安装 hooks", "免环境方案", "仍不在范围内", "无法阻止"):
            self.assertNotIn(prohibited, readme.casefold())

    def test_readme_documents_native_host_uninstall_paths(self) -> None:
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("plugin remove onlyiflow@onlyiflow-dev --json", readme)
        self.assertIn("plugin marketplace remove onlyiflow-dev", readme)
        self.assertIn(
            "claude plugin uninstall onlyiflow@onlyiflow-local --scope user --yes",
            readme,
        )
        self.assertIn("claude plugin marketplace remove onlyiflow-local", readme)
        self.assertNotIn("plugin marketplace update", readme)
        self.assertNotIn("plugin update onlyiflow", readme)
        self.assertIn("## 卸载", readme)
        self.assertNotIn("## 更新现有安装", readme)

    @unittest.skipUnless(
        LOCAL_CONTRACTS_AVAILABLE,
        "local normative contracts are not part of the public repository",
    )
    def test_v040_release_history_remains_documented(self) -> None:
        agents = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        evidence = V030_EVIDENCE.read_text(encoding="utf-8")
        candidate_evidence = V040_CANDIDATE_EVIDENCE.read_text(encoding="utf-8")

        self.assertNotIn("Current source has exactly eleven tools", agents)
        self.assertIn("`v0.4.0`", readme)
        self.assertIn("Status: released as v0.3.0", evidence)
        self.assertIn("Status: released as `v0.4.0`", candidate_evidence)
        self.assertIn(
            "owner-assisted ZCode 3.3.6 Wave acceptance passed", candidate_evidence
        )
        self.assertIn("tagged `v0.4.0`", candidate_evidence)
        self.assertNotIn("当前 GitHub 正式版本为 `v0.1.0`", readme)

    @unittest.skipUnless(
        LOCAL_CONTRACTS_AVAILABLE,
        "local normative contracts are not part of the public repository",
    )
    def test_v050_is_documented_as_the_current_release_without_rewriting_v040_history(
        self,
    ) -> None:
        agents = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        product = (REPOSITORY_ROOT / "docs/product-spec.md").read_text(encoding="utf-8")
        engineering = (REPOSITORY_ROOT / "docs/engineering-spec.md").read_text(
            encoding="utf-8"
        )
        guide = RELEASE_GUIDE.read_text(encoding="utf-8")
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")

        for contents in (agents, product, engineering, guide, readme):
            self.assertIn("0.5.0", contents)
            self.assertIn("flow_close", contents)
            self.assertNotIn("unreleased `0.5.0`", contents.casefold())
        self.assertIn("standard", product)
        self.assertIn("Wave", product)
        self.assertIn("quick", engineering)
        self.assertIn("Gate is the project's fixed final quality", guide)
        self.assertIn("Version `0.5.0` is the current verified GitHub release", agents)
        self.assertIn("Status: released as `v0.5.0`", guide)
        self.assertIn("该版本为当前正式版本", readme)


if __name__ == "__main__":
    unittest.main()
