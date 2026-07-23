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
            by_name["flow_start"]["properties"]["mode"]["enum"],
            ["direct", "wave"],
        )
        self.assertEqual(
            by_name["flow_start"]["properties"]["mode"]["default"],
            "direct",
        )
        self.assertEqual(
            by_name["spec_submit"]["properties"]["flow_id"]["pattern"],
            "^[0-9a-f]{32}$",
        )
        expected_files = by_name["spec_submit"]["properties"]["expected_files"]
        self.assertEqual(expected_files["minItems"], 1)
        self.assertEqual(expected_files["maxItems"], 100)
        self.assertIs(expected_files["uniqueItems"], True)
        gate_checks = by_name["gate_configure"]["properties"]["checks"]
        self.assertEqual(gate_checks["minItems"], 1)
        self.assertEqual(gate_checks["maxItems"], 32)
        gate_check = gate_checks["items"]
        self.assertIs(gate_check["additionalProperties"], False)
        self.assertEqual(
            gate_check["required"],
            ["id", "required", "command", "timeout_seconds"],
        )
        self.assertEqual(gate_check["properties"]["command"]["maxItems"], 32)
        self.assertEqual(gate_check["properties"]["timeout_seconds"]["maximum"], 900)
        packages = by_name["wave_plan_set"]["properties"]["packages"]
        self.assertEqual(packages["minItems"], 1)
        self.assertEqual(packages["maxItems"], 32)
        self.assertIs(packages["items"]["additionalProperties"], False)
        self.assertEqual(
            set(packages["items"]["required"]),
            {
                "id",
                "slug",
                "title",
                "purpose",
                "baseline_assumptions",
                "wave",
                "dependencies",
                "allowed_paths",
                "forbidden_paths",
                "deliverables",
                "non_goals",
                "acceptance",
                "check_ids",
                "runtime_boundaries",
                "requires_authorization",
                "requires_independent_review",
                "condition",
            },
        )
        self.assertEqual(packages["items"]["properties"]["check_ids"]["minItems"], 1)
        record = by_name["work_package_record"]
        self.assertEqual(
            record["properties"]["action"]["enum"],
            [
                "start",
                "submit",
                "request_changes",
                "accept",
                "integrate",
                "interrupt",
                "block",
                "resume",
                "defer",
            ],
        )
        self.assertIs(
            record["properties"]["checks"]["anyOf"][0]["items"]["additionalProperties"],
            False,
        )
        close = by_name["flow_close"]["properties"]
        self.assertEqual(close["action"]["enum"], ["landed", "abandoned"])
        self.assertEqual(
            close["reason_code"]["enum"],
            [
                "external_landing_completed",
                "owner_cancelled",
                "goal_invalidated",
                "scope_drifted",
                "goal_superseded",
            ],
        )

    async def test_single_concise_contract_resource_and_no_prompts(self) -> None:
        async with self.client() as client:
            resources = await client.list_resources()
            prompts = await client.list_prompts()
            first_read = await client.read_resource(CONTRACT_RESOURCE_URI)
            second_read = await client.read_resource(CONTRACT_RESOURCE_URI)

        self.assertEqual(
            [str(resource.uri) for resource in resources], [CONTRACT_RESOURCE_URI]
        )
        self.assertEqual(resources[0].name, "onlyiflow-concise-contract")
        self.assertEqual(resources[0].mimeType, "text/markdown")
        self.assertEqual(prompts, [])
        self.assertEqual(len(first_read), 1)
        self.assertEqual(first_read[0].text, second_read[0].text)

        contract = first_read[0].text
        self.assertLessEqual(len(contract), 1500)
        for expected in [
            "Explicit invocation only.",
            "The host agent owns implementation.",
            "project_status -> flow_start -> implementing",
            "gate_passed -> landing_request -> waiting_owner",
            "waiting_owner -> flow_close -> landed",
            "non-terminal `flow_close -> abandoned`",
            "At most one next action is reported.",
        ]:
            self.assertIn(expected, contract)
        for prohibited in [
            "TODO",
            "stdout",
            "stderr",
            ".onlyiflow/",
            "config.toml",
        ]:
            self.assertNotIn(prohibited, contract)

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

            executable = shutil.which("where.exe")
            self.assertIsNotNone(executable)
            configured = await client.call_tool(
                "gate_configure",
                {
                    "project_root": str(project_root),
                    "checks": [
                        {
                            "id": "tests",
                            "required": True,
                            "command": [executable, "cmd.exe"],
                            "timeout_seconds": 10,
                        }
                    ],
                },
            )
            self.assert_result(configured, expected_ok=True)
            self.assertNotIn(
                executable,
                json.dumps(configured.structured_content),
            )

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
                    "acceptance": "All eight tools complete through stdio.",
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

            closed = await client.call_tool(
                "flow_close",
                {
                    "project_root": str(project_root),
                    "flow_id": flow_id,
                    "action": "landed",
                    "reason_code": "external_landing_completed",
                },
            )
            self.assert_result(closed, expected_ok=True)
            self.assertEqual(closed.structured_content["data"]["state"], "landed")
            self.assertEqual(
                closed.structured_content["data"]["previous_state"], "waiting_owner"
            )
            self.assertFalse(
                closed.structured_content["data"]["external_action_performed"]
            )

            conflict = await client.call_tool(
                "flow_start",
                {
                    "project_root": str(project_root),
                    "risk": "quick",
                    "title": "Conflicting flow",
                },
            )
            self.assert_result(conflict, expected_ok=True)

        for result in [
            status,
            initialized,
            configured,
            started,
            submitted,
            claimed,
            gated,
            landing,
            closed,
            conflict,
        ]:
            self.assertNotIn(str(project_root), json.dumps(result.structured_content))

    async def test_complete_single_package_wave_through_real_stdio(self) -> None:
        project_root = self.temporary_root / "wave project with spaces"
        project_root.mkdir()

        async with self.client() as client:
            await client.call_tool("project_init", {"project_root": str(project_root)})
            executable = shutil.which("where.exe")
            self.assertIsNotNone(executable)
            await client.call_tool(
                "gate_configure",
                {
                    "project_root": str(project_root),
                    "checks": [
                        {
                            "id": "tests",
                            "required": True,
                            "command": [executable, "cmd.exe"],
                            "timeout_seconds": 10,
                        }
                    ],
                },
            )
            started = await client.call_tool(
                "flow_start",
                {
                    "project_root": str(project_root),
                    "risk": "deep",
                    "mode": "wave",
                    "title": "Wave contract",
                },
            )
            self.assert_result(started, expected_ok=True)
            flow_id = started.structured_content["data"]["flow"]["id"]
            submitted = await client.call_tool(
                "spec_submit",
                {
                    "project_root": str(project_root),
                    "flow_id": flow_id,
                    "goal": "Prove one Wave package.",
                    "acceptance": "The package integrates and the final Gate passes.",
                    "boundaries": "The host owns implementation and Git.",
                    "expected_files": ["src/app.py"],
                },
            )
            self.assert_result(submitted, expected_ok=True)
            self.assertEqual(
                submitted.structured_content["next_action"]["tool"],
                "wave_plan_set",
            )
            plan = await client.call_tool(
                "wave_plan_set",
                {
                    "project_root": str(project_root),
                    "flow_id": flow_id,
                    "expected_revision": 0,
                    "packages": [self.wave_package()],
                },
            )
            self.assert_result(plan, expected_ok=True)
            await client.call_tool(
                "flow_claim", {"project_root": str(project_root), "flow_id": flow_id}
            )
            package = await client.call_tool(
                "work_package_status",
                {
                    "project_root": str(project_root),
                    "flow_id": flow_id,
                    "package_id": "P",
                },
            )
            self.assert_result(package, expected_ok=True)
            self.assertEqual(
                package.structured_content["data"]["package"]["purpose"],
                "Implement one bounded package",
            )
            self.assertEqual(
                package.structured_content["data"]["package"]["baseline_assumptions"],
                ["The confirmed Flow spec is the package baseline"],
            )
            self.assertEqual(
                package.structured_content["data"]["package"]["check_ids"],
                ["unit"],
            )
            for action in [
                {"action": "start"},
                {
                    "action": "submit",
                    "base_commit": "a" * 40,
                    "head_commit": "b" * 40,
                    "changed_files": ["src/app.py"],
                    "checks": [
                        {
                            "check_id": "unit",
                            "passed": True,
                            "reason_code": "passed",
                        }
                    ],
                    "known_limits": [],
                },
                {"action": "accept"},
                {"action": "integrate", "head_commit": "b" * 40},
            ]:
                recorded = await client.call_tool(
                    "work_package_record",
                    {
                        "project_root": str(project_root),
                        "flow_id": flow_id,
                        "package_id": "P",
                        **action,
                    },
                )
                self.assert_result(recorded, expected_ok=True)

            status = await client.call_tool(
                "project_status", {"project_root": str(project_root)}
            )
            self.assert_result(status, expected_ok=True)
            self.assertIsNone(
                status.structured_content["data"]["wave_plan"]["current_wave"]
            )
            gated = await client.call_tool(
                "gate_run", {"project_root": str(project_root), "flow_id": flow_id}
            )
            self.assert_result(gated, expected_ok=True)
            self.assertTrue(gated.structured_content["data"]["passed"])

        for result in [started, submitted, plan, package, recorded, status, gated]:
            serialized = json.dumps(result.structured_content)
            self.assertNotIn(str(project_root), serialized)
            self.assertNotIn("where.exe", serialized.casefold())
            self.assertNotIn("stdout", serialized.casefold())

    def wave_package(self) -> dict:
        return {
            "id": "P",
            "slug": "bounded-package",
            "title": "Bounded package",
            "purpose": "Implement one bounded package",
            "baseline_assumptions": ["The confirmed Flow spec is the package baseline"],
            "wave": 0,
            "dependencies": [],
            "allowed_paths": ["src/app.py"],
            "forbidden_paths": [],
            "deliverables": ["Bounded behavior"],
            "non_goals": ["No host automation"],
            "acceptance": ["unit check passes"],
            "check_ids": ["unit"],
            "runtime_boundaries": ["offline"],
            "requires_authorization": [],
            "requires_independent_review": False,
            "condition": None,
        }

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

    def assert_result(self, result: object, *, expected_ok: bool) -> None:
        structured = result.structured_content
        self.assertIsInstance(structured, dict)
        self.assertEqual(structured["ok"], expected_ok)
        self.assertTrue(result.content)
        self.assertEqual(json.loads(result.content[0].text), structured)


if __name__ == "__main__":
    unittest.main()
