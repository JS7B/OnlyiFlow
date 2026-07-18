from __future__ import annotations

import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RELEASE_GUIDE = REPOSITORY_ROOT / "docs/release-guide.md"
TASK7_EVIDENCE = (
    REPOSITORY_ROOT / "docs/evaluations/2026-07-17-task7-release-readiness.md"
)


class ReleaseDocumentationTests(unittest.TestCase):
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
            "docs/product-spec.md",
            "docs/engineering-spec.md",
            "docs/release-guide.md",
        ):
            contents = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
            self.assertNotIn("myself", contents.casefold(), relative_path)
            self.assertIsNone(re.search(r"[A-Z]:\\", contents), relative_path)
            self.assertIsNone(re.search(r"\bTask \d+\b", contents), relative_path)
            self.assertNotIn("At that checkpoint", contents, relative_path)


if __name__ == "__main__":
    unittest.main()
