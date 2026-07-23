from __future__ import annotations

import json
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path

from scripts.build_loader_candidates import build_candidates


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.0"
SERVER_NAME = "onlyiflow"
EXPECTED_TOOLS = [
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
CONTRACT_RESOURCE_URI = "onlyiflow://contract/concise"


class FoundationContractTests(unittest.TestCase):
    def read_json(self, relative_path: str) -> dict:
        return json.loads((REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8"))

    def test_project_metadata_declares_the_minimum_runtime(self) -> None:
        with (REPOSITORY_ROOT / "pyproject.toml").open("rb") as source:
            project = tomllib.load(source)

        self.assertEqual(project["project"]["name"], "onlyiflow")
        self.assertEqual(project["project"]["version"], VERSION)
        self.assertEqual(
            project["project"]["description"],
            "Explicit project-local development-flow state and deterministic landing evidence.",
        )
        self.assertEqual(project["project"]["requires-python"], ">=3.11")
        self.assertEqual(project["project"]["dependencies"], ["fastmcp>=3.4,<4"])
        requirements = (REPOSITORY_ROOT / "requirements.txt").read_text(
            encoding="utf-8"
        )
        self.assertEqual(requirements.splitlines(), project["project"]["dependencies"])
        self.assertEqual(project["build-system"]["requires"], ["setuptools>=68"])
        self.assertEqual(
            project["build-system"]["build-backend"], "setuptools.build_meta"
        )
        self.assertEqual(
            project["tool"]["setuptools"]["packages"]["find"]["where"], ["src"]
        )
        package_init = (REPOSITORY_ROOT / "src/onlyiflow/__init__.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"""OnlyiFlow project-local workflow runtime."""', package_init)
        self.assertIn(f'__version__ = "{VERSION}"', package_init)
        self.assertNotIn("foundation", project["project"]["description"].casefold())
        self.assertNotIn("foundation", package_init.casefold())

    def test_host_manifests_describe_the_formal_plugin(self) -> None:
        manifests = [
            self.read_json("packaging/codex/.codex-plugin/plugin.json"),
            self.read_json("packaging/claude/.claude-plugin/plugin.json"),
            self.read_json("packaging/zcode/.zcode-plugin/plugin.json"),
        ]

        self.assertEqual({manifest["name"] for manifest in manifests}, {"onlyiflow"})
        self.assertEqual({manifest["version"] for manifest in manifests}, {VERSION})
        for manifest in manifests:
            serialized = json.dumps(manifest).lower()
            self.assertNotIn("smoke", serialized)
            self.assertNotIn("disposable", serialized)
            self.assertNotIn("foundation", serialized)
            self.assertEqual(
                manifest["description"],
                "Explicit project-local development-flow state and deterministic "
                "landing evidence.",
            )

        self.assertEqual(
            manifests[0]["interface"]["defaultPrompt"],
            [
                "Use $onlyiflow:onlyiflow to start or resume an explicit workflow "
                "for the current project."
            ],
        )

    def test_host_launchers_use_the_user_selected_python_environment(self) -> None:
        codex_manifest = self.read_json("packaging/codex/.codex-plugin/plugin.json")
        codex_config = self.read_json("packaging/codex/.mcp.json")
        codex = codex_config[SERVER_NAME]
        claude_manifest = self.read_json("packaging/claude/.claude-plugin/plugin.json")
        claude = self.read_json("packaging/claude/.mcp.claude.json")["mcpServers"][
            SERVER_NAME
        ]
        zcode_manifest = self.read_json("packaging/zcode/.zcode-plugin/plugin.json")
        zcode = zcode_manifest["mcpServers"][SERVER_NAME]

        self.assertEqual(set(codex_config), {SERVER_NAME})
        self.assertEqual(codex_manifest["mcpServers"], "./.mcp.json")
        self.assertEqual(codex_manifest["skills"], "./skills/")
        self.assertEqual(codex["cwd"], ".")
        self.assertIn("./server/stdio.py", codex["args"])
        self.assertNotIn("PLUGIN_ROOT", json.dumps(codex))

        self.assertEqual(claude_manifest["mcpServers"], "./.mcp.claude.json")
        self.assertEqual(claude_manifest["skills"], "./skills-claude/")
        self.assertEqual(claude["cwd"], "${CLAUDE_PLUGIN_ROOT}")
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/server/stdio.py", claude["args"])

        self.assertEqual(zcode_manifest["skills"], "skills-claude")
        self.assertEqual(zcode["cwd"], "${ZCODE_PROJECT_DIR}")
        self.assertIn("${ZCODE_PLUGIN_ROOT}/server/stdio.py", zcode["args"])

        for server in [codex, claude, zcode]:
            self.assertEqual(server["command"], "python")
            self.assertEqual(server["args"][:-1], ["-B"])
            self.assertTrue(
                server["args"][-1].replace("\\", "/").endswith("server/stdio.py")
            )
            serialized = json.dumps(server).casefold()
            self.assertNotIn("conda", serialized)
            self.assertNotIn("myself", serialized)
            self.assertEqual(server["env"]["FASTMCP_CHECK_FOR_UPDATES"], "off")
            self.assertEqual(server["env"]["FASTMCP_SHOW_SERVER_BANNER"], "false")

    def test_onlyiflow_skill_is_explicit_and_portable(self) -> None:
        codex_skill = (
            REPOSITORY_ROOT / "packaging/codex/skills/onlyiflow/SKILL.md"
        ).read_text(encoding="utf-8")
        claude_skill = (
            REPOSITORY_ROOT / "packaging/shared/skills-claude/onlyiflow/SKILL.md"
        ).read_text(encoding="utf-8")
        codex_metadata = (
            REPOSITORY_ROOT / "packaging/codex/skills/onlyiflow/agents/openai.yaml"
        ).read_text(encoding="utf-8")

        self.assertIn("name: onlyiflow", codex_skill)
        self.assertIn("name: onlyiflow", claude_skill)
        self.assertNotIn("disable-model-invocation", codex_skill)
        self.assertIn("allow_implicit_invocation: false", codex_metadata)
        self.assertIn("disable-model-invocation: true", claude_skill)
        self.assertEqual(
            codex_skill.split("---", 2)[2].strip(),
            claude_skill.split("---", 2)[2].strip(),
        )
        self.assertIn(
            "Call `project_status` exactly once at the start.",
            codex_skill,
        )
        self.assertNotIn("workflow guidance is not implemented", codex_skill)
        self.assertNotIn("ONLYIFLOW_SMOKE", codex_skill)

    def test_host_candidates_are_isolated_and_self_contained(self) -> None:
        temporary = Path(tempfile.mkdtemp(prefix="OnlyiFlow foundation build "))
        self.addCleanup(shutil.rmtree, temporary)
        roots = build_candidates(temporary / "host candidates")
        marketplace = self.read_json_path(
            roots["codex"].parents[1] / ".agents/plugins/marketplace.json"
        )
        zcode_marketplace = self.read_json_path(
            roots["zcode"].parent / "marketplace.json"
        )

        self.assertEqual(marketplace["name"], "onlyiflow-dev")
        self.assertNotIn("loader", json.dumps(marketplace).lower())
        self.assertEqual(zcode_marketplace["name"], "onlyiflow-dev")
        self.assertEqual(
            zcode_marketplace["plugins"],
            [
                {
                    "name": "onlyiflow",
                    "version": VERSION,
                    "description": (
                        "Explicit project-local development-flow state and "
                        "deterministic landing evidence."
                    ),
                    "source": "./onlyiflow",
                }
            ],
        )
        self.assertEqual(
            {path.name for path in roots["codex"].iterdir()},
            {
                ".codex-plugin",
                ".mcp.json",
                "pyproject.toml",
                "requirements.txt",
                "server",
                "skills",
                "src",
            },
        )
        self.assertEqual(
            {path.name for path in roots["claude"].iterdir()},
            {
                ".claude-plugin",
                ".mcp.claude.json",
                "pyproject.toml",
                "requirements.txt",
                "server",
                "skills-claude",
                "src",
            },
        )
        self.assertEqual(
            {path.name for path in roots["zcode"].iterdir()},
            {
                ".zcode-plugin",
                "pyproject.toml",
                "requirements.txt",
                "server",
                "skills-claude",
                "src",
            },
        )
        for root in roots.values():
            self.assertEqual(
                (root / "requirements.txt").read_text(encoding="utf-8"),
                "fastmcp>=3.4,<4\n",
            )
            self.assertTrue((root / "src/onlyiflow/__init__.py").is_file())
            skill_root = (
                root / "skills/onlyiflow"
                if (root / "skills").exists()
                else root / "skills-claude/onlyiflow"
            )
            self.assertTrue((skill_root / "references/wave-workflow.md").is_file())
            self.assertFalse((root / "src/onlyiflow_smoke").exists())
            self.assertFalse(any(root.rglob("__pycache__")))
            self.assertFalse(
                any("smoke" in path.as_posix() for path in root.rglob("*"))
            )
        references = {
            (
                root / "skills/onlyiflow/references/wave-workflow.md"
                if (root / "skills").exists()
                else root / "skills-claude/onlyiflow/references/wave-workflow.md"
            ).read_text(encoding="utf-8")
            for root in roots.values()
        }
        self.assertEqual(len(references), 1)

    def read_json_path(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))


class ServerLaunchTests(unittest.IsolatedAsyncioTestCase):
    temporary_paths: list[Path] = []

    @classmethod
    def tearDownClass(cls) -> None:
        for path in cls.temporary_paths:
            shutil.rmtree(path)

    async def test_server_starts_through_codex_launcher(self) -> None:
        temporary, roots = self.build_candidates()
        await self.assert_server(
            roots["codex"],
            self.read_json(roots["codex"] / ".mcp.json")[SERVER_NAME],
        )

    async def test_server_starts_through_claude_launcher(self) -> None:
        temporary, roots = self.build_candidates()
        server = self.read_json(roots["claude"] / ".mcp.claude.json")["mcpServers"][
            SERVER_NAME
        ]
        plugin_root = str(roots["claude"])
        server["args"] = [
            value.replace("${CLAUDE_PLUGIN_ROOT}", plugin_root)
            for value in server["args"]
        ]
        server["cwd"] = server["cwd"].replace("${CLAUDE_PLUGIN_ROOT}", plugin_root)
        await self.assert_server(roots["claude"], server)

    async def test_server_starts_through_zcode_launcher(self) -> None:
        temporary, roots = self.build_candidates()
        server = self.read_json(roots["zcode"] / ".zcode-plugin/plugin.json")[
            "mcpServers"
        ][SERVER_NAME]
        plugin_root = str(roots["zcode"])
        project_root = temporary / "ZCode project with spaces"
        project_root.mkdir()
        server["args"] = [
            value.replace("${ZCODE_PLUGIN_ROOT}", plugin_root)
            for value in server["args"]
        ]
        server["cwd"] = server["cwd"].replace("${ZCODE_PROJECT_DIR}", str(project_root))
        await self.assert_server(roots["zcode"], server)

    def build_candidates(self) -> tuple[Path, dict[str, Path]]:
        temporary = Path(tempfile.mkdtemp(prefix="OnlyiFlow foundation launch "))
        self.temporary_paths.append(temporary)
        roots = build_candidates(temporary / "cache with spaces" / VERSION)
        return temporary, roots

    def read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    async def assert_server(self, plugin_root: Path, server: dict) -> None:
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        transport = StdioTransport(
            command=server["command"],
            args=server["args"],
            cwd=str(plugin_root if server["cwd"] == "." else server["cwd"]),
            env={
                **server["env"],
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )
        async with Client(transport, timeout=30) as client:
            tools = await client.list_tools()
            resources = await client.list_resources()
            prompts = await client.list_prompts()
            self.assertEqual([tool.name for tool in tools], EXPECTED_TOOLS)
            self.assertEqual(
                [str(resource.uri) for resource in resources],
                [CONTRACT_RESOURCE_URI],
            )
            self.assertEqual(prompts, [])


if __name__ == "__main__":
    unittest.main()
