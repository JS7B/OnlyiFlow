from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path


sys.dont_write_bytecode = True

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
for source in (REPOSITORY_ROOT, SOURCE_ROOT):
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))

from onlyiflow.runtime import Runtime  # noqa: E402
from scripts.run_claude_user_install_lifecycle import (  # noqa: E402
    EVIDENCE_LABEL,
    MARKETPLACE_NAME,
    PLUGIN_ID,
    PLUGIN_MANIFEST_VERSION,
    PLUGIN_NAME,
    cleanup_lifecycle,
    exact_entry,
    lifecycle_commands,
    list_marketplaces,
    list_plugins,
    onlyiflow_cache_cleanup_target,
    require_plugin,
    run_required,
    unrelated_state,
    wait_for_no_cached_process,
)
from scripts.run_skill_evaluations import (  # noqa: E402
    ProcessResult,
    assistant_excerpt,
    assistant_output,
    called_tools,
    claude_command,
    cleanup_evaluation_workspace,
    event_types,
    infrastructure_failure,
    project_snapshot,
    reported_project_status_unavailable,
    run_process,
)


def evaluate_model_case(
    *,
    process: ProcessResult,
    expected_tools: list[str],
    before: dict,
    after: dict,
    expected_after: dict,
    require_confirmation: bool = False,
    required_response_terms: list[str] | None = None,
) -> tuple[str, list[str], dict]:
    tools = called_tools(process.stdout)
    evidence = {
        "returncode": process.returncode,
        "duration_seconds": process.duration_seconds,
        "timed_out": process.timed_out,
        "event_types": event_types(process.stdout),
        "tool_mentions": tools,
        "before": before,
        "after": after,
    }
    if process.returncode not in (0, None) and process.stderr.strip():
        diagnostic = process.stderr.strip()
        for path, replacement in (
            (Path.home(), "<home>"),
            (REPOSITORY_ROOT, "<repository>"),
            (Path(tempfile.gettempdir()), "<temp>"),
        ):
            raw = str(path)
            diagnostic = diagnostic.replace(raw, replacement)
            diagnostic = diagnostic.replace(raw.replace("\\", "/"), replacement)
        evidence["host_stderr_excerpt"] = diagnostic[-1000:]
    if infrastructure_failure(process):
        return "infrastructure_error", ["host_model_or_network_unavailable"], evidence
    if (
        expected_tools
        and not tools
        and after == before
        and reported_project_status_unavailable(process.stdout)
    ):
        return "infrastructure_error", ["installed_host_tools_unavailable"], evidence
    if process.returncode != 0:
        return "failed", ["installed_host_session_failed"], evidence

    reasons: list[str] = []
    if tools != expected_tools:
        reasons.append("unexpected_onlyiflow_tool_sequence")
    if after != expected_after:
        reasons.append("unexpected_project_state")
    if require_confirmation and not re.search(
        r"confirm|confirmation|确认",
        assistant_output(process.stdout),
        re.IGNORECASE,
    ):
        reasons.append("owner_confirmation_not_requested")
    response = assistant_output(process.stdout).casefold()
    if required_response_terms and any(
        term.casefold() not in response for term in required_response_terms
    ):
        reasons.append("gate_proposal_details_missing")
    if reasons:
        evidence["assistant_excerpt"] = assistant_excerpt(process.stdout)
    return ("passed" if not reasons else "failed"), reasons, evidence


def source_state() -> dict:
    status = run_process(
        ["git", "status", "--porcelain=v1", "-z"],
        cwd=REPOSITORY_ROOT,
        timeout_seconds=30,
    )
    if status.returncode != 0 or status.timed_out:
        raise RuntimeError("source_git_status_failed")
    return {
        "managed": (REPOSITORY_ROOT / ".onlyiflow").exists(),
        "git_status_sha256": hashlib.sha256(status.stdout.encode("utf-8")).hexdigest(),
    }


def gate_configuration_snapshot(project: Path) -> dict:
    snapshot = project_snapshot(project)
    status = Runtime().project_status(str(project))
    if not status["ok"]:
        raise RuntimeError("gate_configuration_status_failed")
    return {**snapshot, "gate_config": status["data"]["gate_config"]}


def run_model_case(
    *,
    case_id: str,
    project: Path,
    prompt: str,
    expected_tools: list[str],
    before: dict,
    expected_after: dict,
    state_reader,
    timeout_seconds: int,
    require_confirmation: bool = False,
    required_response_terms: list[str] | None = None,
) -> dict:
    process = run_process(
        claude_command(
            project,
            prompt,
            enabled=True,
            user_installed=True,
        ),
        cwd=project,
        timeout_seconds=timeout_seconds,
    )
    after = state_reader()
    status, reasons, evidence = evaluate_model_case(
        process=process,
        expected_tools=expected_tools,
        before=before,
        after=after,
        expected_after=expected_after,
        require_confirmation=require_confirmation,
        required_response_terms=required_response_terms,
    )
    return {
        "id": case_id,
        "status": status,
        "reasons": reasons,
        "evidence": evidence,
    }


def require_clean_baseline(
    plugins: list[dict],
    marketplaces: list[dict],
    owned_cache: Path,
) -> None:
    if exact_entry(plugins, "id", PLUGIN_ID) is not None:
        raise RuntimeError("preexisting_onlyiflow_plugin")
    if exact_entry(marketplaces, "name", MARKETPLACE_NAME) is not None:
        raise RuntimeError("preexisting_onlyiflow_marketplace")
    if owned_cache.exists():
        raise RuntimeError("preexisting_onlyiflow_cache")


def installed_inventory(plugin_root: Path) -> dict:
    skills = list(plugin_root.glob("skills-claude/*/SKILL.md"))
    servers = json.loads(
        (plugin_root / ".mcp.claude.json").read_text(encoding="utf-8")
    )["mcpServers"]
    if len(skills) != 1 or set(servers) != {PLUGIN_NAME}:
        raise RuntimeError("installed_component_inventory_invalid")
    return {"skills": len(skills), "mcp_servers": len(servers)}


DEFAULT_REPORT = (
    REPOSITORY_ROOT
    / "build"
    / "v0.4.0-wave-candidate-claude-user-install-acceptance.json"
)


def run_acceptance(marketplace_source: Path, timeout_seconds: int) -> dict:
    from scripts.run_skill_evaluations import cli_prefix

    prefix = cli_prefix("claude")
    cache_root = Path.home() / ".claude" / "plugins" / "cache"
    marketplace_cache_root = (
        Path.home() / ".claude" / "plugins" / "marketplaces" / MARKETPLACE_NAME
    )
    owned_cache = onlyiflow_cache_cleanup_target(
        cache_root / MARKETPLACE_NAME / PLUGIN_NAME,
        cache_root,
    )
    baseline_plugins = list_plugins(prefix, REPOSITORY_ROOT, timeout_seconds)
    baseline_marketplaces = list_marketplaces(prefix, REPOSITORY_ROOT, timeout_seconds)
    require_clean_baseline(baseline_plugins, baseline_marketplaces, owned_cache)
    baseline_unrelated = unrelated_state(baseline_plugins, baseline_marketplaces)

    report = {
        "status": "failed",
        "evidence_label": EVIDENCE_LABEL,
        "plugin_manifest_version": PLUGIN_MANIFEST_VERSION,
        "installed_scope": "user",
        "marketplace_source_retained_during_sessions": False,
        "inventory": None,
        "results": [],
        "unrelated_state_unchanged": False,
        "cleanup_errors": [],
        "remaining_processes": None,
    }
    execution_error: Exception | None = None
    temporary_root = Path(tempfile.mkdtemp(prefix="OnlyiFlow Claude acceptance "))
    staged_marketplace = temporary_root / "marketplace with spaces 中文"
    commands: dict[str, list[str]] | None = None
    try:
        shutil.copytree(marketplace_source, staged_marketplace)
        commands = lifecycle_commands(prefix, staged_marketplace)
        run_required(
            "onlyiflow_marketplace_add",
            commands["marketplace_add"],
            cwd=REPOSITORY_ROOT,
            timeout_seconds=timeout_seconds,
        )
        run_required(
            "onlyiflow_install",
            commands["install"],
            cwd=REPOSITORY_ROOT,
            timeout_seconds=timeout_seconds,
        )
        plugin = require_plugin(prefix, REPOSITORY_ROOT, timeout_seconds, enabled=True)
        if plugin.get("version") != PLUGIN_MANIFEST_VERSION:
            raise RuntimeError("installed_plugin_manifest_version_invalid")
        plugin_root = Path(plugin["installPath"]).resolve()
        if not plugin_root.is_relative_to(owned_cache):
            raise RuntimeError("installed_cache_path_invalid")
        report["inventory"] = installed_inventory(plugin_root)

        unmanaged = temporary_root / "unmanaged project 中文"
        gate_project = temporary_root / "gate configuration project 中文"
        managed = temporary_root / "managed project 中文"
        unmanaged.mkdir()
        gate_project.mkdir()
        managed.mkdir()
        for project in (unmanaged, gate_project, managed):
            (project / "app.py").write_text(
                "def normalize_cache_key(value):\n    return str(value).strip()\n",
                encoding="utf-8",
            )
        (gate_project / "tests").mkdir()
        (gate_project / "tests/test_app.py").write_text(
            (
                "import unittest\n"
                "from app import normalize_cache_key\n\n"
                "class CacheKeyTests(unittest.TestCase):\n"
                "    def test_normalizes_whitespace(self):\n"
                "        self.assertEqual(normalize_cache_key(' value '), 'value')\n"
            ),
            encoding="utf-8",
        )
        gate_initialized = Runtime().project_init(str(gate_project))
        if not gate_initialized["ok"]:
            raise RuntimeError("gate_project_init_failed")
        initialized = Runtime().project_init(str(managed))
        if not initialized["ok"]:
            raise RuntimeError("managed_project_init_failed")
        configured = Runtime().gate_configure(
            str(managed),
            [
                {
                    "id": "tests",
                    "required": True,
                    "command": [sys.executable, "-c", "pass"],
                    "timeout_seconds": 10,
                }
            ],
        )
        if not configured["ok"]:
            raise RuntimeError("managed_gate_configuration_failed")

        report["marketplace_source_retained_during_sessions"] = True

        unmanaged_before = project_snapshot(unmanaged)
        report["results"].append(
            run_model_case(
                case_id="unmanaged-owner-confirmation",
                project=unmanaged,
                prompt=(
                    "/onlyiflow:onlyiflow start a quick flow for the cache-key bug. "
                    "The project may be unmanaged; follow the owner-confirmation "
                    "boundary and stop before initialization."
                ),
                expected_tools=["project_status"],
                before=unmanaged_before,
                expected_after=unmanaged_before,
                state_reader=lambda: project_snapshot(unmanaged),
                timeout_seconds=timeout_seconds,
                require_confirmation=True,
            )
        )
        if report["results"][-1]["status"] != "passed":
            raise RuntimeError("model_case_not_passed")

        gate_before = gate_configuration_snapshot(gate_project)
        report["results"].append(
            run_model_case(
                case_id="gate-configuration-owner-request",
                project=gate_project,
                prompt=(
                    "/onlyiflow:onlyiflow start a quick flow for the cache-key bug. "
                    "The Gate is unconfigured. Propose one required check named tests "
                    "using `python -m unittest discover -s tests -v` with a 120-second "
                    "timeout, then stop for owner confirmation before configuring it."
                ),
                expected_tools=["project_status"],
                before=gate_before,
                expected_after=gate_before,
                state_reader=lambda: gate_configuration_snapshot(gate_project),
                timeout_seconds=timeout_seconds,
                require_confirmation=True,
                required_response_terms=["tests", "python", "120"],
            )
        )
        if report["results"][-1]["status"] != "passed":
            raise RuntimeError("model_case_not_passed")

        gate_confirmed_before = gate_configuration_snapshot(gate_project)
        gate_confirmed_after = {
            **gate_confirmed_before,
            "gate_config": {
                "configured": True,
                "check_count": 1,
                "required_count": 1,
            },
        }
        report["results"].append(
            run_model_case(
                case_id="gate-configuration-owner-confirmation",
                project=gate_project,
                prompt=(
                    "/onlyiflow:onlyiflow I confirm the unchanged project's Gate "
                    "configuration: id tests, required true, command tokens "
                    '["python", "-m", "unittest", "discover", "-s", '
                    '"tests", "-v"], timeout 120 seconds. Configure it now and '
                    "stop before flow_start."
                ),
                expected_tools=["project_status", "gate_configure"],
                before=gate_confirmed_before,
                expected_after=gate_confirmed_after,
                state_reader=lambda: gate_configuration_snapshot(gate_project),
                timeout_seconds=timeout_seconds,
            )
        )
        if report["results"][-1]["status"] != "passed":
            raise RuntimeError("model_case_not_passed")

        managed_before = project_snapshot(managed)
        managed_expected = {
            **managed_before,
            "flows": [{"risk": "quick", "state": "implementing"}],
            "events": managed_before["events"] + 1,
        }
        report["results"].append(
            run_model_case(
                case_id="managed-quick-flow",
                project=managed,
                prompt=(
                    "/onlyiflow:onlyiflow start a quick flow to fix the cache-key "
                    "bug in app.py."
                ),
                expected_tools=["project_status", "flow_start"],
                before=managed_before,
                expected_after=managed_expected,
                state_reader=lambda: project_snapshot(managed),
                timeout_seconds=timeout_seconds,
            )
        )
        if report["results"][-1]["status"] != "passed":
            raise RuntimeError("model_case_not_passed")

        ordinary_before = source_state()
        report["results"].append(
            run_model_case(
                case_id="source-ordinary-zero-trigger",
                project=REPOSITORY_ROOT,
                prompt=(
                    "State the project version from pyproject.toml in one sentence. "
                    "Do not edit files and do not invoke OnlyiFlow."
                ),
                expected_tools=[],
                before=ordinary_before,
                expected_after=ordinary_before,
                state_reader=source_state,
                timeout_seconds=timeout_seconds,
            )
        )
        if report["results"][-1]["status"] != "passed":
            raise RuntimeError("model_case_not_passed")

        source_before = source_state()
        report["results"].append(
            run_model_case(
                case_id="source-explicit-single-status",
                project=REPOSITORY_ROOT,
                prompt=(
                    "/onlyiflow:onlyiflow report the current project status only. "
                    "Do not initialize or start a flow."
                ),
                expected_tools=["project_status"],
                before=source_before,
                expected_after=source_before,
                state_reader=source_state,
                timeout_seconds=timeout_seconds,
            )
        )
    except Exception as error:  # noqa: BLE001 - bounded evidence and cleanup.
        execution_error = error
        report["error_type"] = type(error).__name__
        report["error_code"] = str(error).split(":", 1)[0]
    finally:
        if commands is not None:
            report["cleanup_errors"] = cleanup_lifecycle(
                prefix,
                commands,
                cwd=REPOSITORY_ROOT,
                timeout_seconds=timeout_seconds,
                cache_root=cache_root,
                marketplace_install_root=marketplace_cache_root,
            )
        cleanup_error = cleanup_evaluation_workspace(temporary_root)
        if cleanup_error is not None:
            report["cleanup_errors"].append(cleanup_error)

    final_plugins = list_plugins(prefix, REPOSITORY_ROOT, timeout_seconds)
    final_marketplaces = list_marketplaces(prefix, REPOSITORY_ROOT, timeout_seconds)
    report["unrelated_state_unchanged"] = (
        unrelated_state(final_plugins, final_marketplaces) == baseline_unrelated
    )
    report["remaining_processes"] = wait_for_no_cached_process(owned_cache)
    lifecycle_absent = (
        exact_entry(final_plugins, "id", PLUGIN_ID) is None
        and exact_entry(final_marketplaces, "name", MARKETPLACE_NAME) is None
        and not owned_cache.exists()
        and not owned_cache.parent.exists()
        and not marketplace_cache_root.exists()
    )
    statuses = [result["status"] for result in report["results"]]
    if "infrastructure_error" in statuses:
        report["error_code"] = "host_model_or_network_unavailable"
    elif any(status != "passed" for status in statuses):
        report["error_code"] = "model_acceptance_failed"
    if (
        execution_error is None
        and len(statuses) == 6
        and all(status == "passed" for status in statuses)
        and not report["cleanup_errors"]
        and report["unrelated_state_unchanged"]
        and report["remaining_processes"] == 0
        and lifecycle_absent
    ):
        report["status"] = "passed"
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Claude user-scope OnlyiFlow model acceptance."
    )
    parser.add_argument(
        "--marketplace-root",
        type=Path,
        default=REPOSITORY_ROOT / "build" / "loader-candidates" / "claude-marketplace",
    )
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run_acceptance(args.marketplace_root.resolve(), args.timeout_seconds)
    except Exception as error:  # noqa: BLE001 - preflight evidence.
        report = {
            "status": "failed",
            "evidence_label": EVIDENCE_LABEL,
            "plugin_manifest_version": PLUGIN_MANIFEST_VERSION,
            "error_type": type(error).__name__,
            "error_code": str(error).split(":", 1)[0],
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))
    if any(
        result.get("status") == "infrastructure_error"
        for result in report.get("results", [])
    ):
        return 2
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
