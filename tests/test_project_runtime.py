from __future__ import annotations

import json
import sqlite3
import tempfile
import tomllib
import unittest
from contextlib import closing
from pathlib import Path

import support  # noqa: F401  # Adds the repository source root to sys.path.

from onlyiflow.runtime import Runtime


INITIALIZATION_ENTRIES = [
    ".onlyiflow/onlyiflow.db",
    ".onlyiflow/config.toml",
    ".onlyiflow/specs/",
]


class ProjectRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="OnlyiFlow project runtime "
        )
        self.addCleanup(self.temporary.cleanup)
        self.project_root = Path(self.temporary.name) / "project with spaces"
        self.project_root.mkdir()
        self.runtime = Runtime()

    def test_unmanaged_status_is_read_only(self) -> None:
        before = self.snapshot()

        result = self.runtime.project_status(str(self.project_root))

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["managed"], False)
        self.assertEqual(
            result["data"]["initialization_entries"],
            INITIALIZATION_ENTRIES,
        )
        self.assertEqual(
            result["next_action"],
            {
                "tool": "project_init",
                "reason_code": "owner_confirmation_required",
            },
        )
        self.assertEqual(self.snapshot(), before)
        self.assertNotIn(str(self.project_root), json.dumps(result))

    def test_status_rejects_missing_root_without_writing(self) -> None:
        missing = self.project_root / "missing"

        result = self.runtime.project_status(str(missing))

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "project_root_not_found")
        self.assertTrue(result["error"]["retryable"])
        self.assertFalse(missing.exists())

    def test_status_rejects_file_root(self) -> None:
        file_root = self.project_root / "file.txt"
        file_root.write_text("not a directory", encoding="utf-8")

        result = self.runtime.project_status(str(file_root))

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "project_root_not_directory")

    def test_project_init_creates_exact_layout_and_is_idempotent(self) -> None:
        created = self.runtime.project_init(str(self.project_root))
        repeated = self.runtime.project_init(str(self.project_root))

        self.assertTrue(created["ok"])
        self.assertTrue(created["data"]["created"])
        self.assertEqual(created["data"]["entries"], INITIALIZATION_ENTRIES)
        self.assertEqual(
            created["next_action"],
            {
                "tool": "gate_configure",
                "reason_code": "gate_configuration_required",
            },
        )
        self.assertTrue(repeated["ok"])
        self.assertFalse(repeated["data"]["created"])
        self.assertEqual(repeated["data"]["entries"], INITIALIZATION_ENTRIES)

        state_root = self.project_root / ".onlyiflow"
        self.assertEqual(
            {path.name for path in state_root.iterdir()},
            {"onlyiflow.db", "config.toml", "specs"},
        )
        self.assertEqual(list((state_root / "specs").iterdir()), [])

        with (state_root / "config.toml").open("rb") as source:
            config = tomllib.load(source)
        self.assertEqual(config, {"version": 1, "checks": []})

        with closing(sqlite3.connect(state_root / "onlyiflow.db")) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            user_version = connection.execute("PRAGMA user_version").fetchone()[0]
            foreign_key_tables = {
                row[2]
                for table in ["specs", "gates", "domain_events"]
                for row in connection.execute(f"PRAGMA foreign_key_list({table})")
            }
        self.assertEqual(tables, {"flows", "specs", "gates", "domain_events"})
        self.assertEqual(foreign_key_tables, {"flows"})
        self.assertEqual(user_version, 1)

    def test_managed_status_reports_ready_project_without_absolute_paths(self) -> None:
        self.runtime.project_init(str(self.project_root))

        result = self.runtime.project_status(str(self.project_root))

        self.assertTrue(result["ok"])
        self.assertEqual(
            result["data"],
            {
                "managed": True,
                "active_flow": None,
                "latest_gate": None,
                "gate_config": {
                    "configured": False,
                    "check_count": 0,
                    "required_count": 0,
                },
            },
        )
        self.assertEqual(
            result["next_action"],
            {
                "tool": "gate_configure",
                "reason_code": "gate_configuration_required",
            },
        )
        self.assertNotIn(str(self.project_root), json.dumps(result))

    def snapshot(self) -> list[str]:
        return sorted(
            path.relative_to(self.project_root).as_posix()
            for path in self.project_root.rglob("*")
        )


if __name__ == "__main__":
    unittest.main()
