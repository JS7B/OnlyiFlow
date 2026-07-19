from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


sys.dont_write_bytecode = True

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.run_skill_evaluations import cli_prefix, run_process  # noqa: E402


PLUGIN_ID = "onlyiflow@onlyiflow-local"
PLUGIN_NAME = "onlyiflow"
MARKETPLACE_NAME = "onlyiflow-local"
RELEASE_VERSION = "0.3.0"
UPDATE_VERSION = "0.3.1-test.1"
EXPECTED_TOOLS = [
    "project_status",
    "project_init",
    "gate_configure",
    "flow_start",
    "spec_submit",
    "flow_claim",
    "gate_run",
    "landing_request",
]


def lifecycle_commands(
    prefix: list[str], marketplace_root: Path
) -> dict[str, list[str]]:
    base = [*prefix, "plugin"]
    return {
        "marketplace_add": [
            *base,
            "marketplace",
            "add",
            str(marketplace_root),
            "--scope",
            "user",
        ],
        "install": [*base, "install", PLUGIN_ID, "--scope", "user"],
        "disable": [*base, "disable", PLUGIN_ID, "--scope", "user"],
        "enable": [*base, "enable", PLUGIN_ID, "--scope", "user"],
        "marketplace_update": [
            *base,
            "marketplace",
            "update",
            MARKETPLACE_NAME,
        ],
        "update": [*base, "update", PLUGIN_ID, "--scope", "user"],
        "uninstall": [
            *base,
            "uninstall",
            PLUGIN_ID,
            "--scope",
            "user",
            "--yes",
        ],
        "marketplace_remove": [
            *base,
            "marketplace",
            "remove",
            MARKETPLACE_NAME,
            "--scope",
            "user",
        ],
    }


def bump_marketplace_version(marketplace_root: Path, version: str) -> None:
    plugin_root = marketplace_root / "plugins" / PLUGIN_NAME
    plugin_path = plugin_root / ".claude-plugin" / "plugin.json"
    marketplace_path = marketplace_root / ".claude-plugin" / "marketplace.json"
    plugin = read_json(plugin_path)
    marketplace = read_json(marketplace_path)
    plugin["version"] = version
    entries = [
        entry for entry in marketplace["plugins"] if entry["name"] == PLUGIN_NAME
    ]
    if len(entries) != 1:
        raise ValueError("Marketplace must contain exactly one OnlyiFlow entry.")
    entries[0]["version"] = version
    write_json(plugin_path, plugin)
    write_json(marketplace_path, marketplace)
    (plugin_root / ".onlyiflow-test-version").write_text(
        version + "\n",
        encoding="utf-8",
    )


def unrelated_state(plugins: list[dict], marketplaces: list[dict]) -> dict:
    return {
        "plugins": [entry for entry in plugins if entry.get("id") != PLUGIN_ID],
        "marketplaces": [
            entry for entry in marketplaces if entry.get("name") != MARKETPLACE_NAME
        ],
    }


def onlyiflow_cache_cleanup_target(path: Path, cache_root: Path) -> Path:
    expected = (cache_root / MARKETPLACE_NAME / PLUGIN_NAME).resolve()
    candidate = path.resolve()
    if candidate != expected:
        raise ValueError("Refusing to clean a non-OnlyiFlow cache path.")
    return candidate


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def run_required(
    label: str,
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
) -> str:
    result = run_process(command, cwd=cwd, timeout_seconds=timeout_seconds)
    if result.timed_out:
        raise RuntimeError(f"{label}_timed_out")
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[-1000:]
        raise RuntimeError(f"{label}_failed: {detail}")
    return result.stdout


def cli_json(
    prefix: list[str],
    arguments: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
) -> list[dict]:
    output = run_required(
        "claude_state_read",
        [*prefix, *arguments, "--json"],
        cwd=cwd,
        timeout_seconds=timeout_seconds,
    )
    payload = json.loads(output)
    if not isinstance(payload, list):
        raise RuntimeError("claude_state_shape_invalid")
    return payload


def list_plugins(prefix: list[str], cwd: Path, timeout_seconds: int) -> list[dict]:
    return cli_json(
        prefix,
        ["plugin", "list"],
        cwd=cwd,
        timeout_seconds=timeout_seconds,
    )


def list_marketplaces(prefix: list[str], cwd: Path, timeout_seconds: int) -> list[dict]:
    return cli_json(
        prefix,
        ["plugin", "marketplace", "list"],
        cwd=cwd,
        timeout_seconds=timeout_seconds,
    )


def exact_entry(entries: list[dict], key: str, value: str) -> dict | None:
    matches = [entry for entry in entries if entry.get(key) == value]
    if len(matches) > 1:
        raise RuntimeError("duplicate_onlyiflow_state")
    return matches[0] if matches else None


def require_plugin(
    prefix: list[str], cwd: Path, timeout_seconds: int, *, enabled: bool
) -> dict:
    plugin = exact_entry(list_plugins(prefix, cwd, timeout_seconds), "id", PLUGIN_ID)
    if plugin is None or plugin.get("scope") != "user":
        raise RuntimeError("onlyiflow_user_plugin_missing")
    if plugin.get("enabled") is not enabled:
        raise RuntimeError("onlyiflow_enabled_state_invalid")
    return plugin


async def prove_cached_runtime(
    plugin_root: Path,
    project_root: Path,
    *,
    create_quick_flow: bool,
) -> None:
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    server = read_json(plugin_root / ".mcp.claude.json")["mcpServers"][PLUGIN_NAME]
    root_value = str(plugin_root)
    command = server["command"].replace("${CLAUDE_PLUGIN_ROOT}", root_value)
    arguments = [
        value.replace("${CLAUDE_PLUGIN_ROOT}", root_value) for value in server["args"]
    ]
    cwd = server["cwd"].replace("${CLAUDE_PLUGIN_ROOT}", root_value)
    environment = {**os.environ, **server["env"], "PYTHONDONTWRITEBYTECODE": "1"}
    transport = StdioTransport(
        command=command,
        args=arguments,
        cwd=cwd,
        env=environment,
    )
    async with Client(transport, timeout=60) as client:
        tools = await client.list_tools()
        if [tool.name for tool in tools] != EXPECTED_TOOLS:
            raise RuntimeError("cached_tool_list_invalid")
        status = await client.call_tool(
            "project_status",
            {"project_root": str(project_root)},
        )
        require_tool_ok(status, "project_status")
        if not create_quick_flow:
            return
        initialized = await client.call_tool(
            "project_init",
            {"project_root": str(project_root)},
        )
        require_tool_ok(initialized, "project_init")
        configured = await client.call_tool(
            "gate_configure",
            {
                "project_root": str(project_root),
                "checks": [
                    {
                        "id": "tests",
                        "required": True,
                        "command": ["python", "-c", "pass"],
                        "timeout_seconds": 10,
                    }
                ],
            },
        )
        require_tool_ok(configured, "gate_configure")
        started = await client.call_tool(
            "flow_start",
            {
                "project_root": str(project_root),
                "risk": "quick",
                "title": "Claude cached user plugin lifecycle",
            },
        )
        require_tool_ok(started, "flow_start")
        if started.structured_content["data"]["flow"]["state"] != "implementing":
            raise RuntimeError("cached_quick_flow_state_invalid")


def require_tool_ok(result, tool_name: str) -> None:
    content = result.structured_content
    if not content or content.get("ok") is not True:
        raise RuntimeError(f"cached_{tool_name}_failed")


@contextmanager
def hidden_directories(paths: list[Path]) -> Iterator[None]:
    moves: list[tuple[Path, Path]] = []
    try:
        for index, source in enumerate(paths):
            source = source.resolve()
            hidden = source.with_name(f"{source.name}.onlyiflow-hidden-{index}")
            if hidden.exists():
                raise RuntimeError("source_hide_destination_exists")
            source.rename(hidden)
            moves.append((source, hidden))
        yield
    finally:
        for source, hidden in reversed(moves):
            if hidden.exists() and not source.exists():
                hidden.rename(source)


def wait_for_no_cached_process(plugin_cache_root: Path) -> int:
    if os.name != "nt":
        return 0
    escaped = str(plugin_cache_root).replace("'", "''")
    script = (
        "$target = '" + escaped + "'; "
        "@((Get-CimInstance Win32_Process | Where-Object { "
        "$_.Name -notin @('powershell.exe', 'pwsh.exe') -and "
        "$_.CommandLine -and $_.CommandLine.Contains($target) })).Count"
    )
    count = -1
    for _ in range(40):
        completed = run_process(
            ["powershell.exe", "-NoProfile", "-Command", script],
            cwd=REPOSITORY_ROOT,
            timeout_seconds=15,
        )
        if completed.returncode == 0:
            count = int(completed.stdout.strip() or "0")
            if count == 0:
                return 0
        time.sleep(0.25)
    return count


def cleanup_lifecycle(
    prefix: list[str],
    commands: dict[str, list[str]],
    *,
    cwd: Path,
    timeout_seconds: int,
    cache_root: Path,
    marketplace_install_root: Path,
) -> list[str]:
    errors: list[str] = []
    try:
        if exact_entry(list_plugins(prefix, cwd, timeout_seconds), "id", PLUGIN_ID):
            run_required(
                "onlyiflow_uninstall",
                commands["uninstall"],
                cwd=cwd,
                timeout_seconds=timeout_seconds,
            )
    except Exception as error:  # noqa: BLE001 - cleanup must continue.
        errors.append(f"uninstall:{type(error).__name__}")
    try:
        if exact_entry(
            list_marketplaces(prefix, cwd, timeout_seconds),
            "name",
            MARKETPLACE_NAME,
        ):
            run_required(
                "onlyiflow_marketplace_remove",
                commands["marketplace_remove"],
                cwd=cwd,
                timeout_seconds=timeout_seconds,
            )
    except Exception as error:  # noqa: BLE001 - cleanup must continue.
        errors.append(f"marketplace_remove:{type(error).__name__}")

    cache_target = onlyiflow_cache_cleanup_target(
        cache_root / MARKETPLACE_NAME / PLUGIN_NAME,
        cache_root,
    )
    for label, target in (
        ("cache", cache_target),
        ("marketplace_cache", marketplace_install_root),
    ):
        try:
            if target.exists():
                shutil.rmtree(target)
        except OSError as error:
            errors.append(f"{label}:{type(error).__name__}")
    cache_parent = cache_target.parent
    try:
        if cache_parent.exists():
            if any(cache_parent.iterdir()):
                errors.append("cache_parent:not_empty")
            else:
                cache_parent.rmdir()
    except OSError as error:
        errors.append(f"cache_parent:{type(error).__name__}")
    return errors


def run_lifecycle(marketplace_source: Path, timeout_seconds: int) -> dict:
    prefix = cli_prefix("claude")
    cache_root = Path.home() / ".claude" / "plugins" / "cache"
    marketplace_install_root = (
        Path.home() / ".claude" / "plugins" / "marketplaces" / MARKETPLACE_NAME
    )
    owned_cache = onlyiflow_cache_cleanup_target(
        cache_root / MARKETPLACE_NAME / PLUGIN_NAME,
        cache_root,
    )
    baseline_plugins = list_plugins(prefix, REPOSITORY_ROOT, timeout_seconds)
    baseline_marketplaces = list_marketplaces(prefix, REPOSITORY_ROOT, timeout_seconds)
    if exact_entry(baseline_plugins, "id", PLUGIN_ID) is not None:
        raise RuntimeError("preexisting_onlyiflow_plugin")
    if exact_entry(baseline_marketplaces, "name", MARKETPLACE_NAME) is not None:
        raise RuntimeError("preexisting_onlyiflow_marketplace")
    if owned_cache.exists() or marketplace_install_root.exists():
        raise RuntimeError("preexisting_onlyiflow_cache")
    baseline_unrelated = unrelated_state(baseline_plugins, baseline_marketplaces)

    report = {
        "status": "failed",
        "release_version": RELEASE_VERSION,
        "update_version": UPDATE_VERSION,
        "steps": {},
        "unrelated_state_unchanged": False,
        "cleanup_errors": [],
        "remaining_processes": None,
    }
    with tempfile.TemporaryDirectory(prefix="OnlyiFlow Claude lifecycle ") as temporary:
        temporary_root = Path(temporary)
        staged_marketplace = temporary_root / "marketplace with spaces 中文"
        shutil.copytree(marketplace_source, staged_marketplace)
        commands = lifecycle_commands(prefix, staged_marketplace)
        execution_error: Exception | None = None
        try:
            run_required(
                "onlyiflow_marketplace_add",
                commands["marketplace_add"],
                cwd=REPOSITORY_ROOT,
                timeout_seconds=timeout_seconds,
            )
            report["steps"]["marketplace_added"] = True
            run_required(
                "onlyiflow_install",
                commands["install"],
                cwd=REPOSITORY_ROOT,
                timeout_seconds=timeout_seconds,
            )
            plugin = require_plugin(
                prefix, REPOSITORY_ROOT, timeout_seconds, enabled=True
            )
            if plugin.get("version") != RELEASE_VERSION:
                raise RuntimeError("installed_release_version_invalid")
            plugin_root = Path(plugin["installPath"]).resolve()
            if not plugin_root.is_relative_to(owned_cache):
                raise RuntimeError("installed_cache_path_invalid")
            report["steps"]["installed_user_scope"] = True

            first_project = temporary_root / "first project 中文"
            first_project.mkdir()
            asyncio.run(
                prove_cached_runtime(
                    plugin_root,
                    first_project,
                    create_quick_flow=True,
                )
            )
            report["steps"]["cached_quick_flow"] = True

            marketplace = exact_entry(
                list_marketplaces(prefix, REPOSITORY_ROOT, timeout_seconds),
                "name",
                MARKETPLACE_NAME,
            )
            if marketplace is None:
                raise RuntimeError("installed_marketplace_missing")
            observed_marketplace_root = Path(marketplace["installLocation"]).resolve()
            if (
                marketplace.get("source") != "directory"
                or observed_marketplace_root != staged_marketplace.resolve()
            ):
                raise RuntimeError("marketplace_cache_path_invalid")
            second_project = temporary_root / "second project 中文"
            second_project.mkdir()
            with hidden_directories([observed_marketplace_root]):
                asyncio.run(
                    prove_cached_runtime(
                        plugin_root,
                        second_project,
                        create_quick_flow=False,
                    )
                )
            report["steps"]["cached_package_runtime_files_complete"] = True

            run_required(
                "onlyiflow_disable",
                commands["disable"],
                cwd=REPOSITORY_ROOT,
                timeout_seconds=timeout_seconds,
            )
            require_plugin(prefix, REPOSITORY_ROOT, timeout_seconds, enabled=False)
            report["steps"]["disabled"] = True
            run_required(
                "onlyiflow_enable",
                commands["enable"],
                cwd=REPOSITORY_ROOT,
                timeout_seconds=timeout_seconds,
            )
            require_plugin(prefix, REPOSITORY_ROOT, timeout_seconds, enabled=True)
            report["steps"]["enabled"] = True

            bump_marketplace_version(staged_marketplace, UPDATE_VERSION)
            run_required(
                "onlyiflow_marketplace_update",
                commands["marketplace_update"],
                cwd=REPOSITORY_ROOT,
                timeout_seconds=timeout_seconds,
            )
            run_required(
                "onlyiflow_update",
                commands["update"],
                cwd=REPOSITORY_ROOT,
                timeout_seconds=timeout_seconds,
            )
            updated = require_plugin(
                prefix, REPOSITORY_ROOT, timeout_seconds, enabled=True
            )
            if updated.get("version") != UPDATE_VERSION:
                raise RuntimeError("updated_version_invalid")
            updated_root = Path(updated["installPath"]).resolve()
            if not updated_root.is_relative_to(owned_cache):
                raise RuntimeError("updated_cache_path_invalid")
            if not (updated_root / ".onlyiflow-test-version").is_file():
                raise RuntimeError("updated_cache_marker_missing")
            report["steps"]["updated"] = True
        except Exception as error:  # noqa: BLE001 - cleanup evidence is required.
            execution_error = error
            report["error_type"] = type(error).__name__
            report["error_code"] = str(error).split(":", 1)[0]
        finally:
            report["cleanup_errors"] = cleanup_lifecycle(
                prefix,
                commands,
                cwd=REPOSITORY_ROOT,
                timeout_seconds=timeout_seconds,
                cache_root=cache_root,
                marketplace_install_root=marketplace_install_root,
            )

    final_plugins = list_plugins(prefix, REPOSITORY_ROOT, timeout_seconds)
    final_marketplaces = list_marketplaces(prefix, REPOSITORY_ROOT, timeout_seconds)
    report["unrelated_state_unchanged"] = (
        unrelated_state(final_plugins, final_marketplaces) == baseline_unrelated
    )
    onlyiflow_absent = (
        exact_entry(final_plugins, "id", PLUGIN_ID) is None
        and exact_entry(final_marketplaces, "name", MARKETPLACE_NAME) is None
        and not owned_cache.exists()
        and not owned_cache.parent.exists()
        and not marketplace_install_root.exists()
    )
    report["remaining_processes"] = wait_for_no_cached_process(owned_cache)
    cleanup_complete = not (
        report["cleanup_errors"]
        or not report["unrelated_state_unchanged"]
        or not onlyiflow_absent
        or report["remaining_processes"] != 0
    )
    if execution_error is not None:
        return report
    if not cleanup_complete:
        report["error_type"] = "RuntimeError"
        report["error_code"] = "lifecycle_cleanup_incomplete"
        return report
    report["status"] = "passed"
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify the Claude user-scope OnlyiFlow plugin lifecycle."
    )
    parser.add_argument(
        "--marketplace-root",
        type=Path,
        default=REPOSITORY_ROOT / "build" / "loader-candidates" / "claude-marketplace",
    )
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "build" / "v030-claude-user-install-lifecycle.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report: dict
    try:
        report = run_lifecycle(args.marketplace_root.resolve(), args.timeout_seconds)
    except Exception as error:  # noqa: BLE001 - emit bounded failure evidence.
        report = {
            "status": "failed",
            "error_type": type(error).__name__,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        write_json(args.output, report)
        print(json.dumps(report, ensure_ascii=False))
        raise
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, report)
    print(json.dumps(report, ensure_ascii=False))
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
