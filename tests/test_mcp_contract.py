from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from scripts.build_loader_candidates import build_candidates


EXPECTED_TOOLS = [
    "project_status",
    "project_init",
    "flow_start",
    "spec_submit",
    "flow_claim",
    "gate_run",
    "landing_request",
]


class McpContractTests(unittest.IsolatedAsyncioTestCase):
    temporary_paths: list[Path] = []

    @classmethod
    def tearDownClass(cls) -> None:
        for path in cls.temporary_paths:
            shutil.rmtree(path)

    async def test_tools_list_is_exact_closed_and_bounded(self) -> None:
        async with self.client() as client:
            tools = await client.list_tools()

        self.assertEqual([tool.name for tool in tools], EXPECTED_TOOLS)
        by_name = {tool.name: tool.inputSchema for tool in tools}
        for schema in by_name.values():
            self.assertEqual(schema["type"], "object")
            self.assertIs(schema["additionalProperties"], False)
        for tool in tools:
            self.assertIsNotNone(tool.outputSchema)
            self.assertEqual(tool.outputSchema["type"], "object")
            self.assertEqual(len(tool.outputSchema["oneOf"]), 2)
            for branch in tool.outputSchema["oneOf"]:
                self.assertIs(branch["additionalProperties"], False)

        self.assertEqual(
            by_name["flow_start"]["properties"]["risk"]["enum"],
            ["quick", "standard", "deep"],
        )
        self.assertEqual(
            by_name["flow_start"]["properties"]["title"]["maxLength"],
            200,
        )
        self.assertEqual(
            by_name["spec_submit"]["properties"]["flow_id"]["pattern"],
            "^[0-9a-f]{32}$",
        )
        expected_files = by_name["spec_submit"]["properties"]["expected_files"]
        self.assertEqual(expected_files["minItems"], 1)
        self.assertEqual(expected_files["maxItems"], 100)
        self.assertIs(expected_files["uniqueItems"], True)

    async def test_complete_standard_flow_through_real_stdio(self) -> None:
        project_root = self.temporary_root / "managed project with spaces"
        project_root.mkdir()

        async with self.client() as client:
            status = await client.call_tool(
                "project_status", {"project_root": str(project_root)}
            )
            self.assert_result(status, expected_ok=True)
            self.assertFalse(status.structured_content["data"]["managed"])

            initialized = await client.call_tool(
                "project_init", {"project_root": str(project_root)}
            )
            self.assert_result(initialized, expected_ok=True)

            started = await client.call_tool(
                "flow_start",
                {
                    "project_root": str(project_root),
                    "risk": "standard",
                    "title": "MCP contract",
                },
            )
            self.assert_result(started, expected_ok=True)
            flow_id = started.structured_content["data"]["flow"]["id"]

            submitted = await client.call_tool(
                "spec_submit",
                {
                    "project_root": str(project_root),
                    "flow_id": flow_id,
                    "goal": "Prove the runtime contract.",
                    "acceptance": "All seven tools complete through stdio.",
                    "boundaries": "No host configuration mutation.",
                    "expected_files": ["src/onlyiflow/runtime.py"],
                },
            )
            self.assert_result(submitted, expected_ok=True)

            claimed = await client.call_tool(
                "flow_claim",
                {"project_root": str(project_root), "flow_id": flow_id},
            )
            self.assert_result(claimed, expected_ok=True)

            self.write_passing_gate(project_root)
            gated = await client.call_tool(
                "gate_run",
                {"project_root": str(project_root), "flow_id": flow_id},
            )
            self.assert_result(gated, expected_ok=True)
            self.assertTrue(
                gated.structured_content["data"]["passed"],
                gated.structured_content["data"]["checks"],
            )

            landing = await client.call_tool(
                "landing_request",
                {"project_root": str(project_root), "flow_id": flow_id},
            )
            self.assert_result(landing, expected_ok=True)
            self.assertEqual(
                landing.structured_content["data"]["state"],
                "waiting_owner",
            )
            self.assertFalse(
                landing.structured_content["data"]["direct_git_enforcement"]
            )

            conflict = await client.call_tool(
                "flow_start",
                {
                    "project_root": str(project_root),
                    "risk": "quick",
                    "title": "Conflicting flow",
                },
                raise_on_error=False,
            )
            self.assert_result(conflict, expected_ok=False)
            self.assertTrue(conflict.is_error)
            self.assertEqual(
                conflict.structured_content["error"]["code"],
                "active_flow_exists",
            )

        for result in [
            status,
            initialized,
            started,
            submitted,
            claimed,
            gated,
            landing,
            conflict,
        ]:
            self.assertNotIn(str(project_root), json.dumps(result.structured_content))

    def client(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        roots = build_candidates(self.temporary_root / f"candidate-{uuid4().hex}")
        root = roots["codex"]
        config = json.loads((root / ".mcp.json").read_text(encoding="utf-8"))
        server = config["onlyiflow"]
        transport = StdioTransport(
            command=server["command"],
            args=server["args"],
            cwd=str(root),
            env={
                **server["env"],
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )
        return Client(transport, timeout=30)

    @property
    def temporary_root(self) -> Path:
        if not self.temporary_paths:
            self.temporary_paths.append(
                Path(tempfile.mkdtemp(prefix="OnlyiFlow MCP contract "))
            )
        return self.temporary_paths[0]

    def write_passing_gate(self, project_root: Path) -> None:
        executable = shutil.which("where.exe")
        self.assertIsNotNone(executable)
        command = json.dumps([executable, "cmd.exe"])
        (project_root / ".onlyiflow/config.toml").write_text(
            (
                "version = 1\n"
                "\n"
                "[[checks]]\n"
                'id = "tests"\n'
                "required = true\n"
                f"command = {command}\n"
                "timeout_seconds = 10\n"
            ),
            encoding="utf-8",
        )

    def assert_result(self, result: object, *, expected_ok: bool) -> None:
        structured = result.structured_content
        self.assertIsInstance(structured, dict)
        self.assertEqual(structured["ok"], expected_ok)
        self.assertTrue(result.content)
        self.assertEqual(json.loads(result.content[0].text), structured)


if __name__ == "__main__":
    unittest.main()
