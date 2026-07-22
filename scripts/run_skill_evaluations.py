"""评估各受支持宿主中的显式 Skill 激活与工作流行为。"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


sys.dont_write_bytecode = True

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from onlyiflow.runtime import Runtime  # noqa: E402


EVALUATIONS = REPOSITORY_ROOT / "tests/fixtures/skill_evaluations.json"
RESULTS_ROOT = REPOSITORY_ROOT / "build/task4-evaluation-results"
CODEX_MARKETPLACE = REPOSITORY_ROOT / "build/loader-candidates/codex-marketplace"
CLAUDE_CANDIDATE = (
    REPOSITORY_ROOT / "build/loader-candidates/claude-marketplace/plugins/onlyiflow"
)
TOOLS = (
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
)
CLAUDE_TOOLS = tuple(f"mcp__plugin_onlyiflow_onlyiflow__{tool}" for tool in TOOLS)
INFRASTRUCTURE_PATTERN = re.compile(
    r"stream disconnected|sampling request|timed? out|timeout|network|"
    r"connection|overloaded|rate limit|http 5\d\d|529",
    re.IGNORECASE,
)
UNAVAILABLE_PATTERN = re.compile(
    r"unknown|not found|disabled|unavailable|no such skill|invalid command",
    re.IGNORECASE,
)
WAVE_PACKAGES = [
    {
        "id": "P",
        "slug": "implementation",
        "title": "Normalize cache keys",
        "purpose": "Update cache-key normalization.",
        "baseline_assumptions": ["The public function name is stable."],
        "wave": 0,
        "dependencies": [],
        "allowed_paths": ["app.py"],
        "forbidden_paths": ["tests/"],
        "deliverables": ["Normalized cache-key behavior."],
        "non_goals": ["No test changes."],
        "acceptance": ["Keys are trimmed and lowercased."],
        "check_ids": ["tests"],
        "runtime_boundaries": ["Offline local execution."],
        "requires_authorization": [],
        "requires_independent_review": False,
        "condition": None,
    },
    {
        "id": "Q",
        "slug": "regression",
        "title": "Add cache-key regression coverage",
        "purpose": "Cover the normalized cache-key behavior.",
        "baseline_assumptions": ["Integrated package P is the baseline."],
        "wave": 1,
        "dependencies": ["P"],
        "allowed_paths": ["tests/"],
        "forbidden_paths": ["app.py"],
        "deliverables": ["Cache-key regression tests."],
        "non_goals": ["No implementation changes."],
        "acceptance": ["Tests cover surrounding whitespace and case."],
        "check_ids": ["tests"],
        "runtime_boundaries": ["Offline local execution."],
        "requires_authorization": [],
        "requires_independent_review": False,
        "condition": None,
    },
]


def codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured) if configured else Path.home() / ".codex"


@dataclass(frozen=True)
class ProcessResult:
    returncode: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False

    @property
    def combined(self) -> str:
        return f"{self.stdout}\n{self.stderr}"


def load_evaluations() -> dict:
    return json.loads(EVALUATIONS.read_text(encoding="utf-8"))


def cleanup_evaluation_workspace(
    path: Path,
    *,
    attempts: int = 240,
    delay_seconds: float = 0.5,
) -> str | None:
    for attempt in range(attempts):
        try:
            shutil.rmtree(path)
            return None
        except FileNotFoundError:
            return None
        except OSError as error:
            if attempt == attempts - 1:
                detail = type(error).__name__
                winerror = getattr(error, "winerror", None)
                if winerror is not None:
                    detail += f":winerror_{winerror}"
                return f"evaluation_workspace_cleanup_failed:{detail}"
            time.sleep(delay_seconds)
    return None


def cli_prefix(name: str) -> list[str]:
    if os.name == "nt":
        candidates: list[list[str]] = []
        native = shutil.which(f"{name}.exe")
        if native is not None:
            candidates.append([native])

        if name == "codex":
            local_app_data = os.environ.get("LOCALAPPDATA")
            if local_app_data:
                desktop_bins = Path(local_app_data) / "OpenAI/Codex/bin"
                candidates.extend(
                    [str(path)]
                    for path in sorted(desktop_bins.glob("*/codex.exe"), reverse=True)
                )

        wrapper = shutil.which(f"{name}.cmd")
        if wrapper is not None:
            npm_root = Path(wrapper).resolve().parent
            if name == "codex":
                node = shutil.which("node.exe")
                script = npm_root / "node_modules/@openai/codex/bin/codex.js"
                if node is not None and script.is_file():
                    candidates.append([node, str(script)])
            if name == "claude":
                npm_native = (
                    npm_root / "node_modules/@anthropic-ai/claude-code/bin/claude.exe"
                )
                if npm_native.is_file():
                    candidates.append([str(npm_native)])

        for candidate in candidates:
            try:
                completed = subprocess.run(
                    [*candidate, "--version"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            if completed.returncode == 0:
                return candidate
        raise RuntimeError(f"Safe Windows CLI entry point is unavailable: {name}")

    resolved = shutil.which(name)
    if resolved is None:
        raise RuntimeError(f"Required CLI is unavailable: {name}")
    return [resolved]


def codex_command(project: Path, prompt: str, *, enabled: bool) -> list[str]:
    command = [
        *cli_prefix("codex"),
        "-a",
        "never",
        "-c",
        'model_reasoning_effort="low"',
    ]
    if enabled:
        policy = "plugins.onlyiflow.mcp_servers.onlyiflow"
        command.extend(
            [
                "-c",
                f"{policy}.enabled=true",
                "-c",
                f'{policy}.default_tools_approval_mode="approve"',
                "-c",
                f"{policy}.enabled_tools="
                + json.dumps(list(TOOLS), separators=(",", ":")),
            ]
        )
    command.extend(
        [
            "exec",
            "--ephemeral",
            "--skip-git-repo-check",
            "-s",
            "workspace-write" if enabled else "read-only",
            "-C",
            str(project),
            "--json",
            prompt,
        ]
    )
    return command


def codex_skill_prompt(prompt: str, skill_path: Path) -> str:
    invocation = "$onlyiflow:onlyiflow"
    if not prompt.startswith(invocation):
        raise ValueError("Codex explicit prompt does not start with the Skill name.")
    link = f"[{invocation}]({skill_path.as_posix()})"
    return prompt.replace(invocation, link, 1)


def claude_command(
    project: Path,
    prompt: str,
    *,
    enabled: bool,
    user_installed: bool = False,
) -> list[str]:
    command = [
        *cli_prefix("claude"),
        "-p",
        prompt,
        "--no-session-persistence",
        "--output-format",
        "stream-json",
        "--verbose",
        "--permission-mode",
        "dontAsk",
        "--effort",
        "low",
    ]
    if enabled:
        command.extend(["--allowedTools", ",".join(CLAUDE_TOOLS)])
        if not user_installed:
            command.extend(["--plugin-dir", str(CLAUDE_CANDIDATE)])
    else:
        command.append("--disable-slash-commands")
    return command


def run_process(
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
) -> ProcessResult:
    environment = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "FASTMCP_CHECK_FOR_UPDATES": "off",
        "FASTMCP_SHOW_SERVER_BANNER": "false",
        "MCP_TIMEOUT": "60000",
    }
    started = time.perf_counter()
    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creation_flags,
        start_new_session=os.name != "nt",
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        return ProcessResult(
            returncode=process.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=round(time.perf_counter() - started, 3),
        )
    except subprocess.TimeoutExpired:
        # 终止整个宿主进程树，防止超时的 MCP 子进程残留。
        terminate_process_tree(process.pid)
        stdout, stderr = process.communicate()
        return ProcessResult(
            returncode=None,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=round(time.perf_counter() - started, 3),
            timed_out=True,
        )


def terminate_process_tree(process_id: int) -> None:
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill.exe", "/PID", str(process_id), "/T", "/F"],
                capture_output=True,
                check=False,
                timeout=15,
            )
        except subprocess.TimeoutExpired:
            try:
                os.kill(process_id, signal.SIGTERM)
            except OSError:
                pass
    else:
        try:
            os.killpg(process_id, 9)
        except ProcessLookupError:
            pass


def prepare_project(project: Path, setup: str) -> dict:
    project.mkdir()
    (project / "app.py").write_text(
        "def cache_key(value):\n    return str(value)\n",
        encoding="utf-8",
    )
    runtime = Runtime()
    if setup == "unmanaged":
        return project_snapshot(project)

    initialized = runtime.project_init(str(project))
    require_ok(initialized)
    configure_passing_gate(runtime, project)
    if setup == "managed":
        return project_snapshot(project)
    if setup == "ready":
        flow = require_ok(
            runtime.flow_start(
                str(project),
                risk="standard",
                title="Evaluation ready flow",
            )
        )["flow"]
        require_ok(
            runtime.spec_submit(
                str(project),
                flow_id=flow["id"],
                goal="Continue the prepared evaluation flow.",
                acceptance="The flow reaches implementation.",
                boundaries="Do not edit files during workflow evaluation.",
                expected_files=["app.py"],
            )
        )
        return project_snapshot(project)
    if setup == "implementing_with_gate":
        require_ok(
            runtime.flow_start(
                str(project),
                risk="quick",
                title="Evaluation gate flow",
            )
        )
        return project_snapshot(project)
    if setup in {"wave_draft", "wave_implementing"}:
        tests = project / "tests"
        tests.mkdir()
        (tests / "test_app.py").write_text(
            "# Regression coverage belongs to package Q.\n",
            encoding="utf-8",
        )
        flow = require_ok(
            runtime.flow_start(
                str(project),
                risk="deep",
                title="Normalize cache keys and add regression coverage",
                mode="wave",
            )
        )["flow"]
        if setup == "wave_draft":
            return project_snapshot(project)
        require_ok(
            runtime.spec_submit(
                str(project),
                flow_id=flow["id"],
                goal="Normalize cache keys and add regression coverage.",
                acceptance="All packages integrate before the final Gate.",
                boundaries="No dependency, host configuration, or Git changes.",
                expected_files=["app.py", "tests/test_app.py"],
            )
        )
        require_ok(
            runtime.wave_plan_set(
                str(project),
                flow_id=flow["id"],
                expected_revision=0,
                packages=WAVE_PACKAGES,
            )
        )
        require_ok(runtime.flow_claim(str(project), flow["id"]))
        return project_snapshot(project)
    raise ValueError(f"Unknown evaluation setup: {setup}")


def require_ok(result: dict) -> dict:
    if not result["ok"]:
        raise RuntimeError(json.dumps(result, ensure_ascii=False))
    return result["data"]


def configure_passing_gate(runtime: Runtime, project: Path) -> None:
    where = shutil.which("where.exe")
    if where is None:
        raise RuntimeError("where.exe is required for the deterministic gate fixture.")
    require_ok(
        runtime.gate_configure(
            str(project),
            [
                {
                    "id": "tests",
                    "required": True,
                    "command": [where, "cmd.exe"],
                    "timeout_seconds": 10,
                }
            ],
        )
    )


def project_snapshot(project: Path) -> dict:
    database = project / ".onlyiflow/onlyiflow.db"
    if not database.is_file():
        return {
            "managed": False,
            "flows": [],
            "specs": 0,
            "gate_runs": 0,
            "events": 0,
        }
    with closing(sqlite3.connect(database)) as connection:
        flows = [
            {"risk": risk, "state": state, "mode": "wave" if wave else "direct"}
            for risk, state, wave in connection.execute(
                """
                SELECT flows.risk, flows.state, wave_plans.flow_id
                FROM flows
                LEFT JOIN wave_plans ON wave_plans.flow_id = flows.id
                ORDER BY flows.created_at, flows.id
                """
            )
        ]
        specs = connection.execute("SELECT COUNT(*) FROM specs").fetchone()[0]
        gate_runs = connection.execute(
            "SELECT COUNT(DISTINCT run_id) FROM gates"
        ).fetchone()[0]
        events = connection.execute("SELECT COUNT(*) FROM domain_events").fetchone()[0]
        wave_revision = connection.execute(
            "SELECT MAX(revision) FROM wave_plans"
        ).fetchone()[0]
        work_packages = connection.execute(
            """
            SELECT COUNT(*) FROM work_packages
            WHERE revision = (SELECT MAX(revision) FROM wave_plans)
            """
        ).fetchone()[0]
    return {
        "managed": True,
        "flows": flows,
        "specs": specs,
        "gate_runs": gate_runs,
        "events": events,
        "wave_revision": wave_revision,
        "work_packages": work_packages,
    }


def json_events(output: str) -> list[dict]:
    events = []
    for line in output.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            events.append(value)
    return events


def event_types(output: str) -> list[str]:
    found: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            event_type = value.get("type")
            if isinstance(event_type, str):
                found.add(event_type)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for event in json_events(output):
        visit(event)
    return sorted(found)


def called_tools(output: str) -> list[str]:
    called: list[str] = []

    def visit(value: object) -> None:
        if isinstance(value, dict):
            event_type = str(value.get("type", "")).casefold()
            if event_type in {"tool_use", "tool_call", "mcp_tool_call"}:
                for key in ["name", "tool", "tool_name"]:
                    candidate = value.get(key)
                    if isinstance(candidate, str):
                        for tool in TOOLS:
                            if re.search(rf"(?:^|[^a-z0-9]){tool}$", candidate):
                                called.append(tool)
                                return
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for event in json_events(output):
        if str(event.get("type", "")).casefold() == "item.started":
            continue
        visit(event)
    return called


def assistant_output(output: str) -> str:
    messages: list[str] = []

    def visit(value: object, *, assistant_context: bool = False) -> None:
        if isinstance(value, dict):
            event_type = str(value.get("type", "")).casefold()
            role = str(value.get("role", "")).casefold()
            current_assistant = assistant_context or role == "assistant"
            if event_type == "agent_message" and isinstance(value.get("text"), str):
                messages.append(value["text"])
            if event_type == "result" and isinstance(value.get("result"), str):
                messages.append(value["result"])
            if (
                current_assistant
                and event_type == "text"
                and isinstance(value.get("text"), str)
            ):
                messages.append(value["text"])
            for child in value.values():
                visit(child, assistant_context=current_assistant)
        elif isinstance(value, list):
            for child in value:
                visit(child, assistant_context=assistant_context)

    for event in json_events(output):
        visit(event)
    return "\n".join(messages)


def assistant_excerpt(output: str) -> str:
    text = " ".join(assistant_output(output).split())
    text = re.sub(
        r"(?i)\b[a-z]:[\\/][^\s\"'`]+",
        "<path>",
        text,
    )
    return text[:1000]


def infrastructure_failure(process: ProcessResult) -> bool:
    return process.timed_out or (
        process.returncode not in {0, None}
        and bool(INFRASTRUCTURE_PATTERN.search(process.combined))
    )


def reported_project_status_unavailable(output: str) -> bool:
    text = assistant_output(output).casefold()
    if "project_status" not in text:
        return False
    return any(
        phrase in text
        for phrase in [
            "not exposed",
            "not available",
            "unavailable",
            "not connected",
            "not reachable",
            "did not appear",
            "没有出现在",
            "不可用",
            "未注入",
            "没有被注入",
            "未暴露",
            "未连接",
            "未在本会话中暴露",
            "isn't exposed",
            "isn’t exposed",
            "isn't connected",
            "isn’t connected",
        ]
    )


def evaluate_case(
    *,
    group: str,
    case: dict,
    enabled: bool,
    before: dict,
    after: dict,
    process: ProcessResult,
) -> tuple[str, list[str], dict]:
    tools = called_tools(process.stdout)
    evidence = {
        "returncode": process.returncode,
        "duration_seconds": process.duration_seconds,
        "timed_out": process.timed_out,
        "event_types": event_types(process.stdout),
        "tool_mentions": tools,
        "assistant_excerpt": assistant_excerpt(process.stdout),
        "before": before,
        "after": after,
    }
    if infrastructure_failure(process):
        return "infrastructure_error", ["host_model_or_network_unavailable"], evidence

    if not enabled:
        unavailable = process.returncode == 0 or bool(
            UNAVAILABLE_PATTERN.search(process.combined)
        )
        reasons = []
        if tools:
            reasons.append("disabled_host_exposed_onlyiflow_tool")
        if after != before:
            reasons.append("disabled_host_mutated_onlyiflow_state")
        if not unavailable:
            reasons.append("disabled_host_failed_for_unclassified_reason")
        return ("passed" if not reasons else "failed"), reasons, evidence

    if (
        group in {"explicit", "deep", "wave"}
        and not tools
        and after == before
        and reported_project_status_unavailable(process.stdout)
    ):
        return "infrastructure_error", ["enabled_host_tools_unavailable"], evidence

    if process.returncode != 0:
        return "failed", ["enabled_host_session_failed"], evidence

    reasons = []
    if group == "ordinary":
        if tools:
            reasons.append("ordinary_prompt_called_onlyiflow")
        if after != before:
            reasons.append("ordinary_prompt_mutated_onlyiflow_state")
    elif group == "explicit":
        if tools != case["expected_tools"]:
            reasons.append("unexpected_onlyiflow_tool_sequence")
        state = after["flows"][-1]["state"] if after["flows"] else None
        if state != case["expected_state"]:
            reasons.append("unexpected_flow_state")
        if after["specs"] != case["expected_specs"]:
            reasons.append("unexpected_spec_count")
        if after["gate_runs"] != case["expected_gate_runs"]:
            reasons.append("unexpected_gate_run_count")
    elif group == "deep":
        output = assistant_output(process.stdout).casefold()
        if tools != ["project_status"]:
            reasons.append("deep_prompt_did_not_call_project_status")
        if after != before:
            reasons.append("deep_prompt_mutated_before_confirmation")
        if "deep" not in output:
            reasons.append("deep_risk_not_reported")
        if not re.search(r"confirm|confirmation|确认", output):
            reasons.append("deep_owner_confirmation_not_requested")
    elif group == "wave":
        output = assistant_output(process.stdout).casefold()
        if tools != case["expected_tools"]:
            reasons.append("unexpected_onlyiflow_tool_sequence")
        state = after["flows"][-1]["state"] if after["flows"] else None
        if state != case["expected_state"]:
            reasons.append("unexpected_flow_state")
        if after["specs"] != case["expected_specs"]:
            reasons.append("unexpected_spec_count")
        if after["gate_runs"] != case["expected_gate_runs"]:
            reasons.append("unexpected_gate_run_count")
        if after["wave_revision"] != case["expected_wave_revision"]:
            reasons.append("unexpected_wave_revision")
        if after["work_packages"] != case["expected_package_count"]:
            reasons.append("unexpected_work_package_count")

        phase = case["phase"]
        if phase == "proposal":
            if after != before:
                reasons.append("wave_proposal_mutated_before_confirmation")
            if "deep" not in output or "wave" not in output:
                reasons.append("wave_deep_mode_not_reported")
            complete_plan_terms = [
                r"goal|目标",
                r"invariant|不变量",
                r"non-goal|非目标",
                r"package|工作包",
                r"depend|依赖",
                r"wave",
                r"scope|范围",
                r"accept|验收",
                r"authori[stz]|授权",
            ]
            if any(not re.search(pattern, output) for pattern in complete_plan_terms):
                reasons.append("wave_complete_plan_not_presented")
            if not re.search(r"confirm|confirmation|确认", output):
                reasons.append("wave_plan_confirmation_not_requested")
        elif phase == "confirmation":
            pass
        elif phase == "incomplete_check":
            if "gate_run" in tools:
                reasons.append("wave_gate_called_before_packages_complete")
            if after != before:
                reasons.append("wave_check_mutated_incomplete_flow")
        else:
            raise ValueError(f"Unknown Wave evaluation phase: {phase}")
    else:
        raise ValueError(f"Unknown evaluation group: {group}")
    return ("passed" if not reasons else "failed"), reasons, evidence


def run_case(
    *,
    host: str,
    group: str,
    case: dict,
    enabled: bool,
    timeout_seconds: int,
    cleanup_errors: list[str],
    codex_skill_path: Path | None = None,
) -> dict:
    setup = "unmanaged" if group == "ordinary" else case["setup"]
    root = Path(tempfile.mkdtemp(prefix="OnlyiFlow Task4 evaluation "))
    try:
        project = root / "project with spaces"
        before = prepare_project(project, setup)
        prompt = case["prompt"] if group == "ordinary" else case[f"{host}_prompt"]
        if host == "codex" and enabled and group != "ordinary":
            if codex_skill_path is None:
                raise RuntimeError("Enabled Codex evaluation requires a Skill path.")
            prompt = codex_skill_prompt(prompt, codex_skill_path)
        command = (
            codex_command(project, prompt, enabled=enabled)
            if host == "codex"
            else claude_command(project, prompt, enabled=enabled)
        )
        process = run_process(
            command,
            cwd=project,
            timeout_seconds=timeout_seconds,
        )
        after = project_snapshot(project)
    finally:
        cleanup_error = cleanup_evaluation_workspace(root)
        if cleanup_error is not None:
            cleanup_errors.append(cleanup_error)

    status, reasons, evidence = evaluate_case(
        group=group,
        case=case,
        enabled=enabled,
        before=before,
        after=after,
        process=process,
    )
    return {
        "id": case["id"],
        "group": group,
        "enabled": enabled,
        "status": status,
        "reasons": reasons,
        "evidence": evidence,
    }


class CodexLifecycle:
    def __init__(self) -> None:
        self.marketplace_added = False
        self.plugin_added = False
        self.skill_path: Path | None = None

    def install(self) -> Path:
        self.assert_absent()
        self.run(
            [
                *cli_prefix("codex"),
                "plugin",
                "marketplace",
                "add",
                str(CODEX_MARKETPLACE),
                "--json",
            ]
        )
        self.marketplace_added = True
        installed = json.loads(
            self.run(
                [
                    *cli_prefix("codex"),
                    "plugin",
                    "add",
                    "onlyiflow@onlyiflow-dev",
                    "--json",
                ]
            )
        )
        self.plugin_added = True
        self.skill_path = Path(installed["installedPath"]) / "skills/onlyiflow/SKILL.md"
        if not self.skill_path.is_file():
            raise RuntimeError("Installed Codex Skill path is missing.")
        return self.skill_path

    def cleanup(self) -> list[str]:
        errors = []
        # 先注销插件，再注销市场，最后确认缓存已清除。
        if self.plugin_added:
            try:
                self.run(
                    [
                        *cli_prefix("codex"),
                        "plugin",
                        "remove",
                        "onlyiflow@onlyiflow-dev",
                        "--json",
                    ]
                )
            except RuntimeError as error:
                errors.append(str(error))
        if self.marketplace_added:
            try:
                self.run(
                    [
                        *cli_prefix("codex"),
                        "plugin",
                        "marketplace",
                        "remove",
                        "onlyiflow-dev",
                    ]
                )
            except RuntimeError as error:
                errors.append(str(error))
        try:
            self.assert_absent()
            cache = codex_home() / "plugins/cache/onlyiflow-dev"
            if cache.exists():
                if any(cache.iterdir()):
                    raise RuntimeError(
                        "OnlyiFlow Codex cache still contains files after uninstall."
                    )
                cache.rmdir()
        except RuntimeError as error:
            errors.append(str(error))
        return errors

    def assert_absent(self) -> None:
        plugins = self.run([*cli_prefix("codex"), "plugin", "list", "--json"])
        marketplaces = self.run([*cli_prefix("codex"), "plugin", "marketplace", "list"])
        if "onlyiflow@onlyiflow-dev" in plugins or "onlyiflow-dev" in marketplaces:
            raise RuntimeError(
                "Refusing to replace an existing onlyiflow-dev Codex lifecycle."
            )

    def run(self, command: list[str]) -> str:
        completed = subprocess.run(
            command,
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
            raise RuntimeError(
                f"Codex lifecycle command failed: {completed.stderr.strip()}"
            )
        return completed.stdout


def write_report(host: str, mode: str, results: list[dict], cleanup: list[str]) -> Path:
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = RESULTS_ROOT / f"{host}-{mode}-{timestamp}.json"
    summary = {
        status: sum(result["status"] == status for result in results)
        for status in ["passed", "failed", "infrastructure_error"]
    }
    payload = {
        "host": host,
        "mode": mode,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "summary": summary,
        "cleanup_errors": cleanup,
        "results": results,
    }
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run fresh-session OnlyiFlow Task 4 Skill evaluations."
    )
    parser.add_argument("--host", choices=["codex", "claude"], required=True)
    parser.add_argument(
        "--mode",
        choices=["enabled", "disabled", "both"],
        default="both",
    )
    parser.add_argument(
        "--groups",
        default="ordinary,explicit,deep,wave",
        help="Comma-separated subset of ordinary,explicit,deep,wave.",
    )
    parser.add_argument("--case", help="Run one evaluation case ID.")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument(
        "--allow-codex-plugin-lifecycle",
        action="store_true",
        help="Required for Codex enabled mode; lifecycle is removed in finally.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    groups = [value.strip() for value in args.groups.split(",") if value.strip()]
    if not groups or set(groups) - {"ordinary", "explicit", "deep", "wave"}:
        raise SystemExit("--groups must contain ordinary, explicit, deep, or wave.")
    if args.timeout_seconds < 30:
        raise SystemExit("--timeout-seconds must be at least 30.")
    if (
        args.host == "codex"
        and args.mode in {"enabled", "both"}
        and not args.allow_codex_plugin_lifecycle
    ):
        raise SystemExit(
            "Codex enabled evaluation requires --allow-codex-plugin-lifecycle."
        )

    evaluations = load_evaluations()
    modes = [False, True] if args.mode == "both" else [args.mode == "enabled"]
    lifecycle = CodexLifecycle() if args.host == "codex" else None
    cleanup_errors: list[str] = []
    results: list[dict] = []
    codex_skill_path: Path | None = None
    try:
        for enabled in modes:
            if enabled and lifecycle is not None:
                codex_skill_path = lifecycle.install()
            for group in groups:
                cases = evaluations[group]
                if args.case:
                    cases = [case for case in cases if case["id"] == args.case]
                for case in cases:
                    result = run_case(
                        host=args.host,
                        group=group,
                        case=case,
                        enabled=enabled,
                        timeout_seconds=args.timeout_seconds,
                        cleanup_errors=cleanup_errors,
                        codex_skill_path=codex_skill_path,
                    )
                    results.append(result)
                    print(
                        f"{args.host} enabled={enabled} {group}/{case['id']}: "
                        f"{result['status']}",
                        flush=True,
                    )
                    if result["status"] == "infrastructure_error":
                        raise InterruptedError(
                            "Stopped after the first infrastructure error."
                        )
                    if cleanup_errors:
                        raise InterruptedError("Stopped after the first cleanup error.")
            if enabled and lifecycle is not None:
                cleanup_errors.extend(lifecycle.cleanup())
                lifecycle = CodexLifecycle()
                codex_skill_path = None
    except InterruptedError as error:
        print(str(error), file=sys.stderr)
    finally:
        if lifecycle is not None:
            cleanup_errors.extend(lifecycle.cleanup())

    report = write_report(args.host, args.mode, results, cleanup_errors)
    summary = {
        status: sum(result["status"] == status for result in results)
        for status in ["passed", "failed", "infrastructure_error"]
    }
    print(f"report={report}")
    print(json.dumps(summary, ensure_ascii=False))
    if cleanup_errors or summary["infrastructure_error"]:
        return 2
    if summary["failed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
