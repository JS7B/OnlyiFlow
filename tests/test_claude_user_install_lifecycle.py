from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.run_claude_user_install_lifecycle import (
    DEFAULT_REPORT,
    EVIDENCE_LABEL,
    EXPECTED_TOOLS,
    LIFECYCLE_UPDATE_TEST_VERSION,
    PLUGIN_MANIFEST_VERSION,
    bump_marketplace_version,
    lifecycle_commands,
    onlyiflow_cache_cleanup_target,
    unrelated_state,
)


class ClaudeUserInstallLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_root = Path(
            tempfile.mkdtemp(prefix="OnlyiFlow Claude lifecycle unit ")
        )
        self.addCleanup(shutil.rmtree, self.temporary_root)

    def test_lifecycle_commands_are_exact_and_user_scoped(self) -> None:
        prefix = [r"C:\tools\claude.exe"]
        marketplace_root = self.temporary_root / "marketplace with spaces"
        commands = lifecycle_commands(prefix, marketplace_root)

        self.assertEqual(
            commands,
            {
                "marketplace_add": [
                    *prefix,
                    "plugin",
                    "marketplace",
                    "add",
                    str(marketplace_root),
                    "--scope",
                    "user",
                ],
                "install": [
                    *prefix,
                    "plugin",
                    "install",
                    "onlyiflow@onlyiflow-local",
                    "--scope",
                    "user",
                ],
                "disable": [
                    *prefix,
                    "plugin",
                    "disable",
                    "onlyiflow@onlyiflow-local",
                    "--scope",
                    "user",
                ],
                "enable": [
                    *prefix,
                    "plugin",
                    "enable",
                    "onlyiflow@onlyiflow-local",
                    "--scope",
                    "user",
                ],
                "marketplace_update": [
                    *prefix,
                    "plugin",
                    "marketplace",
                    "update",
                    "onlyiflow-local",
                ],
                "update": [
                    *prefix,
                    "plugin",
                    "update",
                    "onlyiflow@onlyiflow-local",
                    "--scope",
                    "user",
                ],
                "uninstall": [
                    *prefix,
                    "plugin",
                    "uninstall",
                    "onlyiflow@onlyiflow-local",
                    "--scope",
                    "user",
                    "--yes",
                ],
                "marketplace_remove": [
                    *prefix,
                    "plugin",
                    "marketplace",
                    "remove",
                    "onlyiflow-local",
                    "--scope",
                    "user",
                ],
            },
        )

    def test_lifecycle_checks_the_current_exact_tool_inventory(self) -> None:
        self.assertEqual(
            EXPECTED_TOOLS,
            [
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
            ],
        )

    def test_v050_candidate_report_identity_matches_the_manifest_version(self) -> None:
        self.assertEqual(EVIDENCE_LABEL, "v0.5.0-repeatable-flow-candidate")
        self.assertEqual(PLUGIN_MANIFEST_VERSION, "0.5.0")
        self.assertEqual(LIFECYCLE_UPDATE_TEST_VERSION, "0.5.1-test.1")
        self.assertEqual(
            DEFAULT_REPORT.name,
            "v0.5.0-repeatable-flow-candidate-claude-user-install-lifecycle.json",
        )
        self.assertNotIn("v030-claude", DEFAULT_REPORT.name)

    def test_version_bump_updates_marketplace_plugin_and_cache_marker(self) -> None:
        marketplace_root = self.temporary_root / "marketplace"
        plugin_root = marketplace_root / "plugins/onlyiflow"
        manifest_path = plugin_root / ".claude-plugin/plugin.json"
        marketplace_path = marketplace_root / ".claude-plugin/marketplace.json"
        manifest_path.parent.mkdir(parents=True)
        marketplace_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps({"name": "onlyiflow", "version": "0.4.0"}),
            encoding="utf-8",
        )
        marketplace_path.write_text(
            json.dumps(
                {
                    "name": "onlyiflow-local",
                    "plugins": [
                        {
                            "name": "onlyiflow",
                            "source": "./plugins/onlyiflow",
                            "version": "0.4.0",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        bump_marketplace_version(marketplace_root, "0.4.1-test.1")

        self.assertEqual(
            json.loads(manifest_path.read_text(encoding="utf-8"))["version"],
            "0.4.1-test.1",
        )
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
        self.assertEqual(
            marketplace["plugins"][0]["version"],
            "0.4.1-test.1",
        )
        self.assertEqual(
            (plugin_root / ".onlyiflow-test-version").read_text(encoding="utf-8"),
            "0.4.1-test.1\n",
        )

    def test_unrelated_state_excludes_only_exact_onlyiflow_entries(self) -> None:
        plugins = [
            {"id": "onlyiflow@onlyiflow-local", "enabled": True},
            {"id": "onlyiflow-helper@another-market", "enabled": False},
            {"id": "superpowers@claude-plugins-official", "enabled": False},
        ]
        marketplaces = [
            {"name": "onlyiflow-local", "source": "directory"},
            {"name": "onlyiflow-tools", "source": "github"},
            {"name": "claude-plugins-official", "source": "github"},
        ]

        self.assertEqual(
            unrelated_state(plugins, marketplaces),
            {
                "plugins": plugins[1:],
                "marketplaces": marketplaces[1:],
            },
        )

    def test_cache_cleanup_guard_accepts_only_owned_plugin_subtree(self) -> None:
        cache_root = self.temporary_root / ".claude/plugins/cache"
        owned = cache_root / "onlyiflow-local/onlyiflow"
        unrelated = cache_root / "claude-plugins-official/superpowers"

        self.assertEqual(
            onlyiflow_cache_cleanup_target(owned, cache_root),
            owned.resolve(),
        )
        with self.assertRaises(ValueError):
            onlyiflow_cache_cleanup_target(unrelated, cache_root)
        with self.assertRaises(ValueError):
            onlyiflow_cache_cleanup_target(cache_root, cache_root)


if __name__ == "__main__":
    unittest.main()
