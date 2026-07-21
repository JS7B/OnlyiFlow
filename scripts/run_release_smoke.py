"""针对已安装的宿主包运行端到端发布冒烟场景。"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path


sys.dont_write_bytecode = True

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from scripts.run_efficiency_measurements import (  # noqa: E402
    MeasurementFailure,
    MeasurementInfrastructureFailure,
    TASKS,
    database_evidence,
    gate_evidence_is_private,
    measurement_project,
    prepare_project,
    regression_passed,
    require_turn,
    run_turn,
    source_snapshot,
    task5_host_command,
)
from scripts.run_skill_evaluations import (  # noqa: E402
    CLAUDE_CANDIDATE,
    CodexLifecycle,
    cli_prefix,
)
from onlyiflow.runtime import Runtime  # noqa: E402


RESULTS_ROOT = REPOSITORY_ROOT / "build/task6-release-smoke-results"
EXPECTED_SEQUENCES = {
    "ordinary": (),
    "initialization_request": ("project_status",),
    "initialization_confirmation": ("project_status", "project_init"),
    "gate_configuration_request": ("project_status",),
    "gate_configuration_confirmation": ("project_status", "gate_configure"),
    "quick_start": ("project_status", "flow_start"),
    "implementation": (),
    "failed_gate": ("project_status", "gate_run"),
    "repair": (),
    "passed_gate": ("project_status", "gate_run"),
    "landing": ("project_status", "landing_request"),
    "post_unload": (),
}
REQUIRED_CHECKS = (
    "git_project_with_spaces",
    "plugin_loaded",
    "ordinary_zero_activity",
    "initialization_waited_for_confirmation",
    "gate_configuration_waited_for_confirmation",
    "quick_reached_implementing",
    "implementation_host_owned",
    "gate_failed_then_passed",
    "landing_waiting_owner",
    "plugin_unloaded",
    "post_unload_skill_absent",
    "post_unload_tools_absent",
)


class ReleaseSmokeFailure(MeasurementFailure):
    pass


@contextmanager
def release_project():
    with measurement_project("OnlyiFlow Task6 release ") as project:
        prepare_project(project, "quick", managed=False)
        git = shutil.which("git")
        if git is None:
            raise ReleaseSmokeFailure("git_unavailable")
        completed = subprocess.run(
            [git, "init", "--quiet"],
            cwd=project,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        )
        if completed.returncode != 0 or not (project / ".git").is_dir():
            raise ReleaseSmokeFailure("git_initialization_failed")
        yield project


def empty_checks() -> dict[str, bool]:
    return {check: False for check in REQUIRED_CHECKS}


def empty_sequences() -> dict[str, list[str]]:
    return {label: [] for label in EXPECTED_SEQUENCES}


def record_turn(
    turn: dict,
    *,
    label: str,
    edited: bool,
    sequences: dict[str, list[str]],
) -> None:
    sequences[label] = list(turn["tools"])
    require_turn(
        turn,
        tools=list(EXPECTED_SEQUENCES[label]),
        edited=edited,
        label=label,
    )


def gate_configuration_status(project: Path) -> dict:
    result = Runtime().project_status(str(project))
    if not result["ok"] or not result["data"].get("managed"):
        raise ReleaseSmokeFailure("gate_configuration_status_failed")
    return result["data"]["gate_config"]


def run_loaded_smoke(
    *,
    host: str,
    project: Path,
    timeout_seconds: int,
    codex_skill_path: Path | None,
    checks: dict[str, bool],
    sequences: dict[str, list[str]],
) -> None:
    checks["git_project_with_spaces"] = (
        " " in project.name and (project / ".git").is_dir()
    )
    if not checks["git_project_with_spaces"]:
        raise ReleaseSmokeFailure("git_project_contract_failed")
    initial_database = database_evidence(project)
    initial_source = source_snapshot(project)
    # 普通编码回合不得改变工作流状态或源文件。
    ordinary = run_turn(
        host=host,
        project=project,
        prompt=(
            "Explain in one sentence what normalize_cache_key currently does. "
            "Do not edit files and do not invoke OnlyiFlow."
        ),
        enabled=True,
        explicit=False,
        timeout_seconds=timeout_seconds,
        codex_skill_path=codex_skill_path,
    )
    record_turn(
        ordinary,
        label="ordinary",
        edited=False,
        sequences=sequences,
    )
    checks["ordinary_zero_activity"] = (
        database_evidence(project) == initial_database
        and source_snapshot(project) == initial_source
    )
    if not checks["ordinary_zero_activity"]:
        raise ReleaseSmokeFailure("ordinary_activity_detected")

    invocation = "$onlyiflow:onlyiflow" if host == "codex" else "/onlyiflow:onlyiflow"
    initialization_request = run_turn(
        host=host,
        project=project,
        prompt=(
            f"{invocation} start a quick flow for the cache-key bug. The project may be "
            "unmanaged; follow the owner-confirmation boundary and stop before initialization."
        ),
        enabled=True,
        explicit=True,
        timeout_seconds=timeout_seconds,
        codex_skill_path=codex_skill_path,
    )
    record_turn(
        initialization_request,
        label="initialization_request",
        edited=False,
        sequences=sequences,
    )
    checks["plugin_loaded"] = True
    remained_unmanaged = not database_evidence(project)["managed"]

    initialization_confirmation = run_turn(
        host=host,
        project=project,
        prompt=(
            f"{invocation} I confirm initialization of this unchanged project. "
            "Initialize OnlyiFlow now and stop at the next owner action."
        ),
        enabled=True,
        explicit=True,
        timeout_seconds=timeout_seconds,
        codex_skill_path=codex_skill_path,
    )
    record_turn(
        initialization_confirmation,
        label="initialization_confirmation",
        edited=False,
        sequences=sequences,
    )
    initialized = database_evidence(project)
    checks["initialization_waited_for_confirmation"] = (
        remained_unmanaged and initialized["managed"] and initialized["state"] is None
    )
    if not checks["initialization_waited_for_confirmation"]:
        raise ReleaseSmokeFailure("initialization_boundary_failed")

    gate_configuration_request = run_turn(
        host=host,
        project=project,
        prompt=(
            f"{invocation} propose exactly one required Gate for this unchanged project: "
            'ID regression, command ["python", "-s", "-B", "-m", '
            '"unittest", "discover", "-s", "tests", "-v"], timeout '
            "60 seconds. Show the complete proposal and stop before configuration."
        ),
        enabled=True,
        explicit=True,
        timeout_seconds=timeout_seconds,
        codex_skill_path=codex_skill_path,
    )
    record_turn(
        gate_configuration_request,
        label="gate_configuration_request",
        edited=False,
        sequences=sequences,
    )
    remained_unconfigured = gate_configuration_status(project) == {
        "configured": False,
        "check_count": 0,
        "required_count": 0,
    }

    gate_configuration_confirmation = run_turn(
        host=host,
        project=project,
        prompt=(
            f"{invocation} I confirm that exact Gate proposal: ID regression, required true, "
            'command ["python", "-s", "-B", "-m", "unittest", '
            '"discover", "-s", "tests", "-v"], timeout 60 seconds. '
            "Configure it now and stop before starting a flow."
        ),
        enabled=True,
        explicit=True,
        timeout_seconds=timeout_seconds,
        codex_skill_path=codex_skill_path,
    )
    record_turn(
        gate_configuration_confirmation,
        label="gate_configuration_confirmation",
        edited=False,
        sequences=sequences,
    )
    checks["gate_configuration_waited_for_confirmation"] = (
        remained_unconfigured
        and gate_configuration_status(project)
        == {
            "configured": True,
            "check_count": 1,
            "required_count": 1,
        }
        and database_evidence(project)["state"] is None
    )
    if not checks["gate_configuration_waited_for_confirmation"]:
        raise ReleaseSmokeFailure("gate_configuration_boundary_failed")

    test_contents = (project / "tests/test_app.py").read_text(encoding="utf-8")
    quick_start = run_turn(
        host=host,
        project=project,
        prompt=(
            f"{invocation} {TASKS['quick']['start']}. Stop after the workflow state reaches "
            "implementing and do not inspect or edit project files in this turn."
        ),
        enabled=True,
        explicit=True,
        timeout_seconds=timeout_seconds,
        codex_skill_path=codex_skill_path,
    )
    record_turn(
        quick_start,
        label="quick_start",
        edited=False,
        sequences=sequences,
    )
    started = database_evidence(project)
    checks["quick_reached_implementing"] = (
        started["state"] == "implementing" and started["specs"] == 0
    )
    if not checks["quick_reached_implementing"]:
        raise ReleaseSmokeFailure("quick_start_state_failed")

    implementation = run_turn(
        host=host,
        project=project,
        prompt=TASKS["quick"]["implement"],
        enabled=True,
        explicit=False,
        timeout_seconds=timeout_seconds,
        codex_skill_path=codex_skill_path,
    )
    record_turn(
        implementation,
        label="implementation",
        edited=True,
        sequences=sequences,
    )
    tests_unchanged = (project / "tests/test_app.py").read_text(
        encoding="utf-8"
    ) == test_contents
    implemented = regression_passed(project)
    checks["implementation_host_owned"] = tests_unchanged and implemented
    if not checks["implementation_host_owned"]:
        raise ReleaseSmokeFailure("implementation_contract_failed")

    (project / "app.py").write_text(
        TASKS["quick"]["buggy_source"],
        encoding="utf-8",
    )
    if regression_passed(project):
        raise ReleaseSmokeFailure("fault_injection_did_not_fail")

    failed_gate = run_turn(
        host=host,
        project=project,
        prompt=f"{invocation} check the active flow and report the compact gate result",
        enabled=True,
        explicit=True,
        timeout_seconds=timeout_seconds,
        codex_skill_path=codex_skill_path,
    )
    record_turn(
        failed_gate,
        label="failed_gate",
        edited=False,
        sequences=sequences,
    )
    failed_state = database_evidence(project)
    if failed_state["state"] != "implementing" or failed_state["gate_failures"] != 1:
        raise ReleaseSmokeFailure("gate_did_not_catch_fault")

    repair = run_turn(
        host=host,
        project=project,
        prompt=TASKS["quick"]["implement"],
        enabled=True,
        explicit=False,
        timeout_seconds=timeout_seconds,
        codex_skill_path=codex_skill_path,
    )
    record_turn(
        repair,
        label="repair",
        edited=True,
        sequences=sequences,
    )
    repaired = (project / "tests/test_app.py").read_text(
        encoding="utf-8"
    ) == test_contents and regression_passed(project)
    if not repaired:
        raise ReleaseSmokeFailure("repair_contract_failed")

    passed_gate = run_turn(
        host=host,
        project=project,
        prompt=f"{invocation} check the active flow after the regression fix",
        enabled=True,
        explicit=True,
        timeout_seconds=timeout_seconds,
        codex_skill_path=codex_skill_path,
    )
    record_turn(
        passed_gate,
        label="passed_gate",
        edited=False,
        sequences=sequences,
    )
    passed_state = database_evidence(project)
    checks["gate_failed_then_passed"] = (
        passed_state["state"] == "gate_passed"
        and passed_state["gate_runs"] == 2
        and passed_state["gate_failures"] == 1
        and gate_evidence_is_private(project)
    )
    if not checks["gate_failed_then_passed"]:
        raise ReleaseSmokeFailure("gate_did_not_pass_after_repair")

    landing = run_turn(
        host=host,
        project=project,
        prompt=f"{invocation} land the active flow",
        enabled=True,
        explicit=True,
        timeout_seconds=timeout_seconds,
        codex_skill_path=codex_skill_path,
    )
    record_turn(
        landing,
        label="landing",
        edited=False,
        sequences=sequences,
    )
    checks["landing_waiting_owner"] = (
        database_evidence(project)["state"] == "waiting_owner"
    )
    if not checks["landing_waiting_owner"]:
        raise ReleaseSmokeFailure("landing_state_mismatch")


def claude_plugin_absent() -> bool:
    completed = subprocess.run(
        [*cli_prefix("claude"), "plugin", "list"],
        cwd=REPOSITORY_ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise ReleaseSmokeFailure("claude_plugin_list_failed")
    return "onlyiflow" not in completed.stdout.casefold()


def disabled_command_excludes_onlyiflow(host: str, project: Path, prompt: str) -> bool:
    command = task5_host_command(host, project, prompt, enabled=False)
    serialized = " ".join(command).casefold()
    if host == "claude":
        return (
            "--plugin-dir" not in command and "mcp__plugin_onlyiflow" not in serialized
        )
    return "plugins.onlyiflow" not in serialized


def run_post_unload(
    *,
    host: str,
    project: Path,
    timeout_seconds: int,
    checks: dict[str, bool],
    sequences: dict[str, list[str]],
) -> None:
    invocation = "$onlyiflow:onlyiflow" if host == "codex" else "/onlyiflow:onlyiflow"
    prompt = (
        f"{invocation} report the current OnlyiFlow status. Do not edit files or use any "
        "non-OnlyiFlow tool."
    )
    before_database = database_evidence(project)
    before_source = source_snapshot(project)
    # 禁用或卸载后的执行不得保留隐式 OnlyiFlow 能力面。
    turn = run_turn(
        host=host,
        project=project,
        prompt=prompt,
        enabled=False,
        explicit=False,
        timeout_seconds=timeout_seconds,
        codex_skill_path=None,
    )
    record_turn(
        turn,
        label="post_unload",
        edited=False,
        sequences=sequences,
    )
    checks["post_unload_tools_absent"] = (
        database_evidence(project) == before_database
        and source_snapshot(project) == before_source
    )
    checks["post_unload_skill_absent"] = disabled_command_excludes_onlyiflow(
        host,
        project,
        prompt,
    )


def build_report(
    *,
    host: str,
    checks: dict[str, bool],
    sequences: dict[str, list[str]],
    cleanup_errors: list[str],
    error: str | None,
) -> dict:
    normalized_checks = {
        check: bool(checks.get(check, False)) for check in REQUIRED_CHECKS
    }
    normalized_sequences = {
        label: list(sequences.get(label, [])) for label in EXPECTED_SEQUENCES
    }
    sequences_passed = all(
        normalized_sequences[label] == list(expected)
        for label, expected in EXPECTED_SEQUENCES.items()
    )
    passed = (
        all(normalized_checks.values())
        and sequences_passed
        and not cleanup_errors
        and error is None
    )
    report = {
        "host": host,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "status": "passed" if passed else "failed",
        "checks": normalized_checks,
        "sequences": normalized_sequences,
        "cleanup_errors": cleanup_errors,
    }
    if error is not None:
        report["error"] = error
    return report


def write_report(report: dict) -> Path:
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = RESULTS_ROOT / f"{report['host']}-{timestamp}.json"
    path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the OnlyiFlow Task 6 release smoke for Codex or Claude."
    )
    parser.add_argument("--host", choices=["codex", "claude"], required=True)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument(
        "--allow-codex-plugin-lifecycle",
        action="store_true",
        help="Required for Codex; the temporary lifecycle is removed in finally.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout_seconds < 30:
        raise SystemExit("--timeout-seconds must be at least 30.")
    if args.host == "codex" and not args.allow_codex_plugin_lifecycle:
        raise SystemExit("Codex smoke requires --allow-codex-plugin-lifecycle.")

    lifecycle = CodexLifecycle() if args.host == "codex" else None
    codex_skill_path: Path | None = None
    checks = empty_checks()
    sequences = empty_sequences()
    cleanup_errors: list[str] = []
    error: str | None = None
    infrastructure_error = False

    with release_project() as project:
        try:
            if lifecycle is not None:
                codex_skill_path = lifecycle.install()
            elif not CLAUDE_CANDIDATE.is_dir() or not claude_plugin_absent():
                raise ReleaseSmokeFailure("claude_candidate_or_lifecycle_invalid")
            run_loaded_smoke(
                host=args.host,
                project=project,
                timeout_seconds=args.timeout_seconds,
                codex_skill_path=codex_skill_path,
                checks=checks,
                sequences=sequences,
            )
        except MeasurementInfrastructureFailure as caught:
            error = str(caught)
            infrastructure_error = True
        except MeasurementFailure as caught:
            error = str(caught)
        except RuntimeError:
            error = "plugin_lifecycle_failed"
        finally:
            # 若未清理运行器拥有的生命周期状态，发布证据即为无效。
            if lifecycle is not None:
                raw_cleanup = lifecycle.cleanup()
                if raw_cleanup:
                    cleanup_errors.append("codex_lifecycle_cleanup_failed")
                    for cleanup_error in raw_cleanup:
                        print(cleanup_error, file=sys.stderr)

        try:
            if lifecycle is not None:
                lifecycle.assert_absent()
                checks["plugin_unloaded"] = not (
                    codex_skill_path is not None and codex_skill_path.exists()
                )
            else:
                checks["plugin_unloaded"] = claude_plugin_absent()
            run_post_unload(
                host=args.host,
                project=project,
                timeout_seconds=args.timeout_seconds,
                checks=checks,
                sequences=sequences,
            )
        except MeasurementInfrastructureFailure as caught:
            if error is None:
                error = str(caught)
            infrastructure_error = True
        except (MeasurementFailure, RuntimeError) as caught:
            if error is None:
                error = str(caught)

    report = build_report(
        host=args.host,
        checks=checks,
        sequences=sequences,
        cleanup_errors=cleanup_errors,
        error=error,
    )
    path = write_report(report)
    print(f"report={path}")
    print(
        json.dumps(
            {
                "status": report["status"],
                "checks_passed": sum(report["checks"].values()),
                "checks_total": len(report["checks"]),
                "cleanup_errors": len(cleanup_errors),
            },
            ensure_ascii=False,
        )
    )
    if report["status"] == "passed":
        return 0
    return 2 if infrastructure_error else 1


if __name__ == "__main__":
    raise SystemExit(main())
