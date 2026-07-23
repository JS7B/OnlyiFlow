from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.build_loader_candidates import build_candidates


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.0"


class ClaudeUserInstallPackagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_root = Path(
            tempfile.mkdtemp(prefix="OnlyiFlow Claude user install ")
        )
        self.addCleanup(shutil.rmtree, self.temporary_root)

    def test_host_templates_are_not_auto_discovered_from_source_root(self) -> None:
        auto_discovered_roots = (
            ".codex-plugin",
            ".claude-plugin",
            ".zcode-plugin",
            ".mcp.json",
            ".mcp.claude.json",
            "skills",
            "skills-claude",
        )
        for relative_path in auto_discovered_roots:
            with self.subTest(relative_path=relative_path):
                self.assertFalse((REPOSITORY_ROOT / relative_path).exists())

        expected_templates = (
            "packaging/codex/.codex-plugin/plugin.json",
            "packaging/codex/.mcp.json",
            "packaging/codex/skills/onlyiflow/SKILL.md",
            "packaging/claude/.claude-plugin/plugin.json",
            "packaging/claude/.mcp.claude.json",
            "packaging/zcode/.zcode-plugin/plugin.json",
            "packaging/shared/skills-claude/onlyiflow/SKILL.md",
        )
        for relative_path in expected_templates:
            with self.subTest(relative_path=relative_path):
                self.assertTrue((REPOSITORY_ROOT / relative_path).is_file())

    def test_builder_emits_one_claude_marketplace_plugin(self) -> None:
        output_root = self.temporary_root / "loader candidates"
        roots = build_candidates(output_root)
        plugin_root = output_root / "claude-marketplace/plugins/onlyiflow"
        marketplace_path = (
            output_root / "claude-marketplace/.claude-plugin/marketplace.json"
        )

        self.assertEqual(roots["claude"], plugin_root.resolve())
        marketplace = self.read_json(marketplace_path)
        self.assertEqual(marketplace["name"], "onlyiflow-local")
        self.assertEqual(marketplace["owner"], {"name": "OnlyiFlow"})
        self.assertEqual(
            marketplace["description"],
            "Local user-scope distribution for OnlyiFlow.",
        )
        self.assertEqual(
            marketplace["plugins"],
            [
                {
                    "name": "onlyiflow",
                    "source": "./plugins/onlyiflow",
                    "version": VERSION,
                    "strict": True,
                }
            ],
        )
        plugin = self.read_json(plugin_root / ".claude-plugin/plugin.json")
        self.assertEqual(plugin["version"], VERSION)

    def test_fresh_candidate_builds_have_identical_file_content(self) -> None:
        first_root = self.temporary_root / "first"
        second_root = self.temporary_root / "second"
        build_candidates(first_root)
        build_candidates(second_root)

        self.assertEqual(
            self.file_manifest(first_root),
            self.file_manifest(second_root),
        )

    def read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def file_manifest(self, root: Path) -> dict[str, str]:
        return {
            path.relative_to(root).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }


if __name__ == "__main__":
    unittest.main()
