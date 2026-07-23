from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

import support  # noqa: F401  # Adds the repository source root to sys.path.
from scripts.run_skill_evaluations import cleanup_evaluation_workspace


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMMAND_ONLY_TOKENS = [
    "C:/External/OnlyiFlow/private-runner.exe",
    "ONLYIFLOW_COMMAND_SENTINEL",
    "ONLYIFLOW_STDOUT_SENTINEL",
    "ONLYIFLOW_STDERR_SENTINEL",
    "ONLYIFLOW_PROMPT_SENTINEL",
    "ONLYIFLOW_TRANSCRIPT_SENTINEL",
]


class WavePrivacyTests(unittest.IsolatedAsyncioTestCase):
    temporary_paths: list[Path] = []

    async def asyncSetUp(self) -> None:
        self.temporary_root = Path(tempfile.mkdtemp(prefix="OnlyiFlow Wave privacy "))
        self.temporary_paths.append(self.temporary_root)
        self.project_root = self.temporary_root / "project with spaces"
        self.project_root.mkdir()

    @classmethod
    def tearDownClass(cls) -> None:
        for path in cls.temporary_paths:
            cleanup_error = cleanup_evaluation_workspace(
                path,
                attempts=50,
                delay_seconds=0.1,
            )
            if cleanup_error is not None:
                raise AssertionError(cleanup_error)

    async def test_wave_mcp_and_sqlite_keep_gate_material_only_in_config(
        self,
    ) -> None:
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        transport = StdioTransport(
            command=sys.executable,
            args=["-B", str(REPOSITORY_ROOT / "server/stdio.py")],
            cwd=str(REPOSITORY_ROOT),
            env={
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "FASTMCP_CHECK_FOR_UPDATES": "off",
                "FASTMCP_SHOW_SERVER_BANNER": "false",
            },
        )
        results = []
        async with Client(transport, timeout=30) as client:
            results.append(
                await client.call_tool(
                    "project_init", {"project_root": str(self.project_root)}
                )
            )
            results.append(
                await client.call_tool(
                    "gate_configure",
                    {
                        "project_root": str(self.project_root),
                        "checks": [
                            {
                                "id": "privacy-check",
                                "required": True,
                                "command": COMMAND_ONLY_TOKENS,
                                "timeout_seconds": 30,
                            }
                        ],
                    },
                )
            )
            started = await client.call_tool(
                "flow_start",
                {
                    "project_root": str(self.project_root),
                    "risk": "deep",
                    "mode": "wave",
                    "title": "Verify bounded Wave persistence",
                },
            )
            results.append(started)
            flow_id = started.structured_content["data"]["flow"]["id"]
            results.append(
                await client.call_tool(
                    "spec_submit",
                    {
                        "project_root": str(self.project_root),
                        "flow_id": flow_id,
                        "goal": "Verify bounded Wave persistence.",
                        "acceptance": "The confirmed package evidence remains compact.",
                        "boundaries": "The host owns execution and external Git actions.",
                        "expected_files": ["src/privacy.py"],
                    },
                )
            )
            results.append(
                await client.call_tool(
                    "wave_plan_set",
                    {
                        "project_root": str(self.project_root),
                        "flow_id": flow_id,
                        "expected_revision": 0,
                        "packages": [self.package_contract()],
                    },
                )
            )
            results.append(
                await client.call_tool(
                    "flow_claim",
                    {"project_root": str(self.project_root), "flow_id": flow_id},
                )
            )
            results.append(
                await client.call_tool(
                    "work_package_status",
                    {
                        "project_root": str(self.project_root),
                        "flow_id": flow_id,
                        "package_id": "P",
                    },
                )
            )
            for action in [
                {"action": "start"},
                {
                    "action": "submit",
                    "base_commit": "a" * 40,
                    "head_commit": "b" * 40,
                    "changed_files": ["src/privacy.py"],
                    "checks": [
                        {
                            "check_id": "privacy-check",
                            "passed": True,
                            "reason_code": "passed",
                        }
                    ],
                    "known_limits": [],
                },
                {"action": "accept"},
                {"action": "integrate", "head_commit": "b" * 40},
            ]:
                results.append(
                    await client.call_tool(
                        "work_package_record",
                        {
                            "project_root": str(self.project_root),
                            "flow_id": flow_id,
                            "package_id": "P",
                            **action,
                        },
                    )
                )
            results.append(
                await client.call_tool(
                    "project_status", {"project_root": str(self.project_root)}
                )
            )

        config = self.project_root / ".onlyiflow/config.toml"
        config_text = config.read_text(encoding="utf-8")
        for token in COMMAND_ONLY_TOKENS:
            self.assertIn(token, config_text)

        response_text = "\n".join(
            json.dumps(result.structured_content, ensure_ascii=False)
            + "\n"
            + "\n".join(getattr(block, "text", "") for block in result.content)
            for result in results
        )
        self.assertNotIn(str(self.project_root), response_text)
        for token in COMMAND_ONLY_TOKENS:
            self.assertNotIn(token, response_text)

        database = self.project_root / ".onlyiflow/onlyiflow.db"
        with closing(sqlite3.connect(database)) as connection:
            connection.row_factory = sqlite3.Row
            database_text = self.database_text(connection)
            for table in ("work_packages", "package_events"):
                columns = {
                    row[1].casefold()
                    for row in connection.execute(f"PRAGMA table_info({table})")
                }
                for prohibited in (
                    "command",
                    "stdout",
                    "stderr",
                    "prompt",
                    "transcript",
                    "external_path",
                ):
                    self.assertFalse(
                        any(prohibited in column for column in columns),
                        f"{table} exposes prohibited column {prohibited}",
                    )

        for token in COMMAND_ONLY_TOKENS:
            self.assertNotIn(token, database_text)
        self.assertNotIn(str(self.project_root), database_text)

        for state_file in (self.project_root / ".onlyiflow").rglob("*"):
            if not state_file.is_file() or state_file == config:
                continue
            content = state_file.read_bytes()
            for token in COMMAND_ONLY_TOKENS:
                self.assertNotIn(token.encode("utf-8"), content)

    def database_text(self, connection: sqlite3.Connection) -> str:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        payload = {}
        for table in tables:
            payload[table] = [
                dict(row) for row in connection.execute(f'SELECT * FROM "{table}"')
            ]
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def package_contract(self) -> dict:
        return {
            "id": "P",
            "slug": "privacy",
            "title": "Verify bounded persistence",
            "purpose": "Record only the confirmed package contract and compact evidence.",
            "baseline_assumptions": ["The project Gate is already configured"],
            "wave": 0,
            "dependencies": [],
            "allowed_paths": ["src/privacy.py"],
            "forbidden_paths": [],
            "deliverables": ["Bounded persistence evidence"],
            "non_goals": ["No host lifecycle mutation"],
            "acceptance": ["privacy check passes"],
            "check_ids": ["privacy-check"],
            "runtime_boundaries": ["offline"],
            "requires_authorization": [],
            "requires_independent_review": False,
            "condition": None,
        }


if __name__ == "__main__":
    unittest.main()
