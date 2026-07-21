"""Measure bounded workflow efficiency and Gate value across supported hosts."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path


sys.dont_write_bytecode = True

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from onlyiflow.runtime import Runtime  # noqa: E402
from scripts.run_skill_evaluations import (  # noqa: E402
    CLAUDE_TOOLS,
    CodexLifecycle,
    called_tools,
    claude_command,
    codex_command,
    codex_skill_prompt,
    infrastructure_failure,
    run_process,
)


RESULTS_ROOT = REPOSITORY_ROOT / "build/task5-measurement-results"
APPROVED_METRIC_KEYS = {
    "wall_clock_seconds",
    "model_turns",
    "mcp_calls_before_first_code_edit",
    "total_mcp_calls",
    "gate_failures_caught_before_landing",
    "task_success",
    "regression_result",
}
BUILTIN_CLAUDE_TOOLS = ("Read", "Edit", "Write", "Bash", "Glob", "Grep")
EXCLUDED_SOURCE_PARTS = {".git", ".onlyiflow", "__pycache__", ".pytest_cache"}
PRIVATE_GATE_KEYS = {
    "command",
    "cwd",
    "stdout",
    "stderr",
    "prompt",
    "transcript",
    "credential",
    "project_root",
}

TASKS = {
    "quick": {
        "buggy_source": (
            "def normalize_cache_key(value):\n    return str(value).strip()\n"
        ),
        "test_source": (
            "import unittest\n\n"
            "from app import normalize_cache_key\n\n\n"
            "class CacheKeyTests(unittest.TestCase):\n"
            "    def test_key_is_trimmed_and_casefolded(self):\n"
            "        self.assertEqual(normalize_cache_key('  User-ID  '), 'user-id')\n\n\n"
            "if __name__ == '__main__':\n"
            "    unittest.main()\n"
        ),
        "start": (
            "start a quick flow for the localized cache-key normalization bug in app.py; "
            "acceptance is that surrounding whitespace is removed and keys are lowercase"
        ),
        "implement": (
            "Fix app.py so normalize_cache_key removes surrounding whitespace and returns "
            "a lowercase key. Run the existing unittest suite. Do not edit the tests and do "
            "not invoke OnlyiFlow for this ordinary implementation request."
        ),
    },
    "standard": {
        "buggy_source": (
            "def paginate(items, page, per_page):\n"
            "    start = page * per_page\n"
            "    return items[start:start + per_page]\n"
        ),
        "test_source": (
            "import unittest\n\n"
            "from app import paginate\n\n\n"
            "class PaginationTests(unittest.TestCase):\n"
            "    def test_pages_are_one_based(self):\n"
            "        items = ['a', 'b', 'c', 'd', 'e']\n"
            "        self.assertEqual(paginate(items, 1, 2), ['a', 'b'])\n"
            "        self.assertEqual(paginate(items, 2, 2), ['c', 'd'])\n\n\n"
            "if __name__ == '__main__':\n"
            "    unittest.main()\n"
        ),
        "start": (
            "start a standard flow to correct the one-based pagination boundary in app.py; "
            "acceptance is that pages 1 and 2 return the first and second slices, the existing "
            "tests pass, and tests remain unchanged"
        ),
        "implement": (
            "Fix the one-based pagination boundary in app.py and run the existing unittest "
            "suite. Do not edit the tests and do not invoke OnlyiFlow for this ordinary "
            "implementation request."
        ),
    },
}


class MeasurementFailure(RuntimeError):
    pass


class MeasurementInfrastructureFailure(MeasurementFailure):
    pass


def source_snapshot(project: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    # Workflow state is excluded so source edits can be measured independently.
    for path in sorted(project.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        relative = path.relative_to(project)
        if any(part in EXCLUDED_SOURCE_PARTS for part in relative.parts):
            continue
        snapshot[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def summarize_flow(
    turns: list[dict],
    *,
    gate_failures: int,
    task_success: bool,
    regression_passed: bool | None,
) -> dict:
    first_edit = next(
        (index for index, turn in enumerate(turns) if turn["edited"]),
        None,
    )
    before_edit = turns if first_edit is None else turns[:first_edit]
    return {
        "wall_clock_seconds": round(
            sum(turn["duration_seconds"] for turn in turns),
            3,
        ),
        "model_turns": len(turns),
        "mcp_calls_before_first_code_edit": (
            None
            if first_edit is None
            else sum(len(turn["tools"]) for turn in before_edit)
        ),
        "total_mcp_calls": sum(len(turn["tools"]) for turn in turns),
        "gate_failures_caught_before_landing": gate_failures,
        "task_success": task_success,
        "regression_result": (
            "not_applicable"
            if regression_passed is None
            else "passed"
            if regression_passed
            else "failed"
        ),
    }


def evaluate_budgets(evidence: dict) -> dict[str, bool]:
    baseline = evidence["baseline"]
    initialization = evidence["initialization"]
    quick = evidence["quick"]
    standard = evidence["standard"]
    return {
        "enabled_uninvoked_zero_overhead": (
            baseline["additional_model_turns"] == 0
            and baseline["enabled_mcp_calls"] == 0
        ),
        "managed_quick_two_call_start": quick["start_calls"] == 2,
        "first_use_initialization_reported_separately": initialization[
            "reported_separately"
        ],
        "quick_no_spec_or_plan": quick["specs"] == 0 and quick["plans"] == 0,
        "standard_one_compact_spec": standard["specs"] == 1,
        "no_automatic_review_loop": (
            quick["automatic_review_turns"] == 0
            and standard["automatic_review_turns"] == 0
        ),
        "intentional_gate_failed_then_passed": (
            quick["gate_failed_then_passed"] and standard["gate_failed_then_passed"]
        ),
        "gate_evidence_private": (
            quick["gate_evidence_private"] and standard["gate_evidence_private"]
        ),
    }


def build_report(
    *,
    host: str,
    measurements: dict[str, dict],
    budgets: dict[str, bool],
    cleanup_errors: list[str],
) -> dict:
    for metrics in measurements.values():
        if set(metrics) != APPROVED_METRIC_KEYS:
            raise ValueError(
                "Task 5 reports may contain only approved aggregate metrics."
            )
    passed = (
        all(metric["task_success"] for metric in measurements.values())
        and all(budgets.values())
        and not cleanup_errors
    )
    return {
        "host": host,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "status": "passed" if passed else "failed",
        "measurements": measurements,
        "acceptance_budgets": budgets,
        "cleanup_errors": cleanup_errors,
    }


def task5_host_command(
    host: str,
    project: Path,
    prompt: str,
    *,
    enabled: bool,
) -> list[str]:
    if host == "codex":
        return codex_command(project, prompt, enabled=enabled)
    command = claude_command(project, prompt, enabled=enabled)
    allowed = ",".join([*(CLAUDE_TOOLS if enabled else ()), *BUILTIN_CLAUDE_TOOLS])
    if "--allowedTools" in command:
        index = command.index("--allowedTools")
        command[index + 1] = allowed
    else:
        index = command.index("--disable-slash-commands")
        command[index:index] = ["--allowedTools", allowed]
    return command


@contextmanager
def measurement_project(prefix: str):
    temporary_root = Path(tempfile.mkdtemp(prefix=prefix)).resolve()
    expected_parent = Path(tempfile.gettempdir()).resolve()
    if temporary_root.parent != expected_parent:
        raise MeasurementFailure("temporary_workspace_outside_expected_root")
    project = temporary_root / "project with spaces"
    try:
        yield project
    finally:
        for attempt in range(5):
            try:
                shutil.rmtree(temporary_root)
                break
            except PermissionError:
                if attempt == 4:
                    raise MeasurementFailure("temporary_workspace_cleanup_failed")
                time.sleep(0.25)


def run_turn(
    *,
    host: str,
    project: Path,
    prompt: str,
    enabled: bool,
    explicit: bool,
    timeout_seconds: int,
    codex_skill_path: Path | None,
) -> dict:
    rendered_prompt = prompt
    if host == "codex" and enabled and explicit:
        if codex_skill_path is None:
            raise MeasurementFailure("Codex Skill path is missing.")
        rendered_prompt = codex_skill_prompt(prompt, codex_skill_path)
    before = source_snapshot(project)
    process = run_process(
        task5_host_command(host, project, rendered_prompt, enabled=enabled),
        cwd=project,
        timeout_seconds=timeout_seconds,
    )
    if infrastructure_failure(process):
        raise MeasurementInfrastructureFailure("host_model_or_network_unavailable")
    if process.returncode != 0:
        raise MeasurementFailure("host_session_failed")
    return {
        "duration_seconds": process.duration_seconds,
        "tools": called_tools(process.stdout),
        "edited": source_snapshot(project) != before,
    }


def require_turn(
    turn: dict,
    *,
    tools: list[str],
    edited: bool,
    label: str,
) -> None:
    if turn["tools"] != tools:
        expected = json.dumps(tools, separators=(",", ":"))
        actual = json.dumps(turn["tools"], separators=(",", ":"))
        raise MeasurementFailure(
            f"{label}_unexpected_mcp_sequence:expected={expected},actual={actual}"
        )
    if turn["edited"] is not edited:
        raise MeasurementFailure(f"{label}_unexpected_edit_state")


def prepare_project(project: Path, task_name: str, *, managed: bool) -> None:
    task = TASKS[task_name]
    project.mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "app.py").write_text(task["buggy_source"], encoding="utf-8")
    (project / "tests/test_app.py").write_text(
        task["test_source"],
        encoding="utf-8",
    )
    if not managed:
        return
    result = Runtime().project_init(str(project))
    if not result["ok"]:
        raise MeasurementFailure("fixture_initialization_failed")
    write_gate_config(project)


def write_gate_config(project: Path) -> None:
    result = Runtime().gate_configure(
        str(project),
        [
            {
                "id": "regression",
                "required": True,
                "command": [
                    sys.executable,
                    "-s",
                    "-B",
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    "tests",
                    "-v",
                ],
                "timeout_seconds": 60,
            }
        ],
    )
    if not result["ok"]:
        raise MeasurementFailure("fixture_gate_configuration_failed")


def regression_passed(project: Path) -> bool:
    completed = subprocess.run(
        [
            sys.executable,
            "-s",
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-v",
        ],
        cwd=project,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=60,
        check=False,
    )
    return completed.returncode == 0


def database_evidence(project: Path) -> dict:
    database = project / ".onlyiflow/onlyiflow.db"
    if not database.is_file():
        return {
            "managed": False,
            "state": None,
            "specs": 0,
            "gate_runs": 0,
            "gate_failures": 0,
            "latest_gate": [],
        }
    with closing(sqlite3.connect(database)) as connection:
        row = connection.execute(
            "SELECT state FROM flows ORDER BY created_at, id DESC LIMIT 1"
        ).fetchone()
        specs = connection.execute("SELECT COUNT(*) FROM specs").fetchone()[0]
        gate_runs = connection.execute(
            "SELECT COUNT(DISTINCT run_id) FROM gates"
        ).fetchone()[0]
        gate_failures = connection.execute(
            "SELECT COUNT(DISTINCT run_id) FROM gates WHERE required = 1 AND passed = 0"
        ).fetchone()[0]
        latest_run = connection.execute(
            "SELECT run_id FROM gates ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        latest_gate = []
        if latest_run is not None:
            latest_gate = [
                {
                    "check_id": check_id,
                    "passed": bool(passed),
                    "reason_code": reason_code,
                    "exit_code": exit_code,
                }
                for check_id, passed, reason_code, exit_code in connection.execute(
                    "SELECT check_id, passed, reason_code, exit_code "
                    "FROM gates WHERE run_id = ? ORDER BY rowid",
                    (latest_run[0],),
                )
            ]
    return {
        "managed": True,
        "state": row[0] if row else None,
        "specs": specs,
        "gate_runs": gate_runs,
        "gate_failures": gate_failures,
        "latest_gate": latest_gate,
    }


def gate_evidence_is_private(project: Path) -> bool:
    result = Runtime().project_status(str(project))
    if not result["ok"]:
        return False

    # Recursively reject command-like fields and leaked fixture paths.
    def visit(value: object) -> bool:
        if isinstance(value, dict):
            if any(str(key).casefold() in PRIVATE_GATE_KEYS for key in value):
                return False
            return all(visit(child) for child in value.values())
        if isinstance(value, list):
            return all(visit(child) for child in value)
        if isinstance(value, str) and project.as_posix().casefold() in value.casefold():
            return False
        return True

    return visit(result["data"].get("latest_gate"))


def plan_artifact_count(project: Path) -> int:
    return sum("plan" in path.casefold() for path in source_snapshot(project))


def host_invocation(host: str) -> str:
    return "$onlyiflow:onlyiflow" if host == "codex" else "/onlyiflow:onlyiflow"


def run_baseline(
    *,
    host: str,
    enabled: bool,
    timeout_seconds: int,
    codex_skill_path: Path | None,
) -> dict:
    with measurement_project("OnlyiFlow Task5 baseline ") as project:
        prepare_project(project, "quick", managed=True)
        before = database_evidence(project)
        turn = run_turn(
            host=host,
            project=project,
            prompt=(
                "Explain in one sentence what normalize_cache_key currently does. "
                "Do not edit files and do not invoke OnlyiFlow."
            ),
            enabled=enabled,
            explicit=False,
            timeout_seconds=timeout_seconds,
            codex_skill_path=codex_skill_path,
        )
        require_turn(turn, tools=[], edited=False, label="baseline")
        success = database_evidence(project) == before
    return summarize_flow(
        [turn],
        gate_failures=0,
        task_success=success,
        regression_passed=None,
    )


def run_initialization(
    *,
    host: str,
    timeout_seconds: int,
    codex_skill_path: Path | None,
) -> tuple[dict, dict]:
    with measurement_project("OnlyiFlow Task5 initialization ") as project:
        prepare_project(project, "quick", managed=False)
        invocation = host_invocation(host)
        first = run_turn(
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
        require_turn(
            first,
            tools=["project_status"],
            edited=False,
            label="initialization_request",
        )
        if database_evidence(project)["managed"]:
            raise MeasurementFailure("initialization_happened_before_confirmation")
        second = run_turn(
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
        require_turn(
            second,
            tools=["project_status", "project_init"],
            edited=False,
            label="initialization_confirmation",
        )
        state = database_evidence(project)
        success = state["managed"] and state["state"] is None
    metrics = summarize_flow(
        [first, second],
        gate_failures=0,
        task_success=success,
        regression_passed=None,
    )
    return metrics, {"reported_separately": True}


def run_representative_flow(
    *,
    host: str,
    risk: str,
    timeout_seconds: int,
    codex_skill_path: Path | None,
) -> tuple[dict, dict]:
    task = TASKS[risk]
    with measurement_project(f"OnlyiFlow Task5 {risk} ") as project:
        prepare_project(project, risk, managed=True)
        test_contents = (project / "tests/test_app.py").read_text(encoding="utf-8")
        invocation = host_invocation(host)
        start = run_turn(
            host=host,
            project=project,
            prompt=f"{invocation} {task['start']}",
            enabled=True,
            explicit=True,
            timeout_seconds=timeout_seconds,
            codex_skill_path=codex_skill_path,
        )
        start_tools = (
            ["project_status", "flow_start"]
            if risk == "quick"
            else ["project_status", "flow_start", "spec_submit", "flow_claim"]
        )
        require_turn(start, tools=start_tools, edited=False, label=f"{risk}_start")
        started = database_evidence(project)
        if started["state"] != "implementing":
            raise MeasurementFailure(f"{risk}_did_not_reach_implementing")

        implement = run_turn(
            host=host,
            project=project,
            prompt=task["implement"],
            enabled=True,
            explicit=False,
            timeout_seconds=timeout_seconds,
            codex_skill_path=codex_skill_path,
        )
        require_turn(implement, tools=[], edited=True, label=f"{risk}_implementation")
        if (project / "tests/test_app.py").read_text(encoding="utf-8") != test_contents:
            raise MeasurementFailure(f"{risk}_implementation_changed_tests")
        if not regression_passed(project):
            raise MeasurementFailure(f"{risk}_initial_implementation_failed")

        (project / "app.py").write_text(task["buggy_source"], encoding="utf-8")
        if regression_passed(project):
            raise MeasurementFailure(f"{risk}_fault_injection_did_not_fail")

        check_failed = run_turn(
            host=host,
            project=project,
            prompt=f"{invocation} check the active flow and report the compact gate result",
            enabled=True,
            explicit=True,
            timeout_seconds=timeout_seconds,
            codex_skill_path=codex_skill_path,
        )
        require_turn(
            check_failed,
            tools=["project_status", "gate_run"],
            edited=False,
            label=f"{risk}_failed_gate",
        )
        failed_state = database_evidence(project)
        if (
            failed_state["state"] != "implementing"
            or failed_state["gate_failures"] != 1
        ):
            raise MeasurementFailure(f"{risk}_gate_did_not_catch_fault")

        repair = run_turn(
            host=host,
            project=project,
            prompt=task["implement"],
            enabled=True,
            explicit=False,
            timeout_seconds=timeout_seconds,
            codex_skill_path=codex_skill_path,
        )
        require_turn(repair, tools=[], edited=True, label=f"{risk}_repair")
        if (project / "tests/test_app.py").read_text(encoding="utf-8") != test_contents:
            raise MeasurementFailure(f"{risk}_repair_changed_tests")
        repaired = regression_passed(project)

        check_passed = run_turn(
            host=host,
            project=project,
            prompt=f"{invocation} check the active flow after the regression fix",
            enabled=True,
            explicit=True,
            timeout_seconds=timeout_seconds,
            codex_skill_path=codex_skill_path,
        )
        require_turn(
            check_passed,
            tools=["project_status", "gate_run"],
            edited=False,
            label=f"{risk}_passed_gate",
        )
        if database_evidence(project)["state"] != "gate_passed":
            compact = database_evidence(project)
            raise MeasurementFailure(
                f"{risk}_gate_did_not_pass:"
                + json.dumps(compact["latest_gate"], separators=(",", ":"))
            )

        land = run_turn(
            host=host,
            project=project,
            prompt=f"{invocation} land the active flow",
            enabled=True,
            explicit=True,
            timeout_seconds=timeout_seconds,
            codex_skill_path=codex_skill_path,
        )
        require_turn(
            land,
            tools=["project_status", "landing_request"],
            edited=False,
            label=f"{risk}_landing",
        )
        final = database_evidence(project)
        task_success = repaired and final["state"] == "waiting_owner"
        evidence = {
            "start_calls": len(start["tools"]),
            "specs": final["specs"],
            "plans": plan_artifact_count(project),
            "automatic_review_turns": 0,
            "gate_failed_then_passed": (
                final["gate_runs"] == 2 and final["gate_failures"] == 1
            ),
            "gate_evidence_private": gate_evidence_is_private(project),
        }
        turns = [start, implement, check_failed, repair, check_passed, land]
        metrics = summarize_flow(
            turns,
            gate_failures=final["gate_failures"],
            task_success=task_success,
            regression_passed=repaired,
        )
    return metrics, evidence


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
        description="Measure OnlyiFlow Task 5 efficiency and deterministic gate value."
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
        raise SystemExit("Codex measurements require --allow-codex-plugin-lifecycle.")

    lifecycle = CodexLifecycle() if args.host == "codex" else None
    codex_skill_path: Path | None = None
    cleanup_errors: list[str] = []
    measurements: dict[str, dict] = {}
    evidence: dict[str, dict] = {}
    error: MeasurementFailure | None = None
    try:
        measurements["baseline_disabled"] = run_baseline(
            host=args.host,
            enabled=False,
            timeout_seconds=args.timeout_seconds,
            codex_skill_path=None,
        )
        if lifecycle is not None:
            codex_skill_path = lifecycle.install()
        measurements["baseline_enabled"] = run_baseline(
            host=args.host,
            enabled=True,
            timeout_seconds=args.timeout_seconds,
            codex_skill_path=codex_skill_path,
        )
        evidence["baseline"] = {
            "additional_model_turns": (
                measurements["baseline_enabled"]["model_turns"]
                - measurements["baseline_disabled"]["model_turns"]
            ),
            "enabled_mcp_calls": measurements["baseline_enabled"]["total_mcp_calls"],
        }
        measurements["initialization"], evidence["initialization"] = run_initialization(
            host=args.host,
            timeout_seconds=args.timeout_seconds,
            codex_skill_path=codex_skill_path,
        )
        measurements["quick"], evidence["quick"] = run_representative_flow(
            host=args.host,
            risk="quick",
            timeout_seconds=args.timeout_seconds,
            codex_skill_path=codex_skill_path,
        )
        measurements["standard"], evidence["standard"] = run_representative_flow(
            host=args.host,
            risk="standard",
            timeout_seconds=args.timeout_seconds,
            codex_skill_path=codex_skill_path,
        )
    except MeasurementFailure as caught:
        error = caught
        print(f"measurement_error={caught}", file=sys.stderr)
    finally:
        # The temporary Codex lifecycle is runner-owned regardless of outcome.
        if lifecycle is not None:
            raw_cleanup = lifecycle.cleanup()
            if raw_cleanup:
                cleanup_errors.append("codex_lifecycle_cleanup_failed")
                for cleanup_error in raw_cleanup:
                    print(cleanup_error, file=sys.stderr)

    if error is not None:
        return 2 if isinstance(error, MeasurementInfrastructureFailure) else 1

    budgets = evaluate_budgets(evidence)
    report = build_report(
        host=args.host,
        measurements=measurements,
        budgets=budgets,
        cleanup_errors=cleanup_errors,
    )
    path = write_report(report)
    print(f"report={path}")
    print(
        json.dumps(
            {
                "status": report["status"],
                "budgets_passed": sum(budgets.values()),
                "budgets_total": len(budgets),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
