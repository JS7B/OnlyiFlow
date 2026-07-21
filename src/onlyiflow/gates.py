"""校验、持久化并执行确定性的项目 Gate 检查。"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .contracts import DomainError


CHECK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
MAX_COMMAND_PARTS = 32
MAX_COMMAND_PART_LENGTH = 1024
MAX_CHECKS = 32
MAX_TIMEOUT_SECONDS = 900


@dataclass(frozen=True)
class GateCheck:
    check_id: str
    required: bool
    command: list[str]
    timeout_seconds: int


def load_gate_checks(config_path: Path) -> list[GateCheck]:
    checks = load_gate_configuration(config_path)
    if not checks:
        raise DomainError(
            code="gate_checks_missing",
            message="No gate checks are configured.",
            retryable=True,
            next_action={
                "tool": "gate_configure",
                "reason_code": "gate_configuration_required",
            },
        )
    return checks


def load_gate_configuration(config_path: Path) -> list[GateCheck]:
    try:
        with config_path.open("rb") as source:
            config = tomllib.load(source)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise gate_config_invalid() from error

    if set(config) - {"version", "checks"} or config.get("version") != 1:
        raise gate_config_invalid()
    raw_checks = config.get("checks")
    if not isinstance(raw_checks, list):
        raise gate_config_invalid()
    return _validate_gate_checks(raw_checks, allow_empty=True)


def configure_gate_checks(config_path: Path, raw_checks: list[dict]) -> list[GateCheck]:
    checks = _validate_gate_checks(raw_checks, allow_empty=False)
    content = serialize_gate_configuration(checks)
    temporary_path: Path | None = None
    try:
        # 临时文件与目标文件置于同一目录，以保证 os.replace 的原子替换。
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=config_path.parent,
            prefix=".config.toml.",
            suffix=".tmp",
            delete=False,
        ) as destination:
            temporary_path = Path(destination.name)
            destination.write(content)
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary_path, config_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return checks


def gate_config_summary(config_path: Path) -> dict:
    checks = load_gate_configuration(config_path)
    return {
        "configured": bool(checks),
        "check_count": len(checks),
        "required_count": sum(check.required for check in checks),
    }


def serialize_gate_configuration(checks: list[GateCheck]) -> str:
    lines = ["version = 1"]
    for check in checks:
        lines.extend(
            [
                "",
                "[[checks]]",
                f"id = {json.dumps(check.check_id)}",
                f"required = {str(check.required).lower()}",
                f"command = {json.dumps(check.command)}",
                f"timeout_seconds = {check.timeout_seconds}",
            ]
        )
    return "\n".join(lines) + "\n"


def _validate_gate_checks(
    raw_checks: list[dict],
    *,
    allow_empty: bool,
) -> list[GateCheck]:
    if (
        not isinstance(raw_checks, list)
        or (not allow_empty and not raw_checks)
        or len(raw_checks) > MAX_CHECKS
    ):
        raise gate_config_invalid()

    checks: list[GateCheck] = []
    seen: set[str] = set()
    for raw in raw_checks:
        if not isinstance(raw, dict) or set(raw) != {
            "id",
            "required",
            "command",
            "timeout_seconds",
        }:
            raise gate_config_invalid()
        check_id = raw["id"]
        required = raw["required"]
        command = raw["command"]
        timeout_seconds = raw["timeout_seconds"]
        if (
            not isinstance(check_id, str)
            or not CHECK_ID_PATTERN.fullmatch(check_id)
            or check_id.casefold() in seen
            or type(required) is not bool
            or not isinstance(command, list)
            or not command
            or len(command) > MAX_COMMAND_PARTS
            or any(
                not isinstance(part, str)
                or not part
                or len(part) > MAX_COMMAND_PART_LENGTH
                for part in command
            )
            or type(timeout_seconds) is not int
            or not 1 <= timeout_seconds <= MAX_TIMEOUT_SECONDS
        ):
            raise gate_config_invalid()
        seen.add(check_id.casefold())
        checks.append(
            GateCheck(
                check_id=check_id,
                required=required,
                command=command,
                timeout_seconds=timeout_seconds,
            )
        )
    return checks


def run_gate_checks(checks: list[GateCheck], project_root: Path) -> list[dict]:
    return [run_gate_check(check, project_root) for check in checks]


def run_gate_check(check: GateCheck, project_root: Path) -> dict:
    started = time.perf_counter()
    exit_code: int | None = None
    try:
        # Gate 证据只记录紧凑元数据，不保留命令输出。
        completed = subprocess.run(
            check.command,
            cwd=project_root,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=check.timeout_seconds,
            check=False,
        )
        exit_code = completed.returncode
        passed = exit_code == 0
        reason_code = "check_passed" if passed else "check_failed"
    except subprocess.TimeoutExpired:
        passed = False
        reason_code = "check_timeout"
    except OSError:
        passed = False
        reason_code = "check_launch_error"

    duration_ms = max(0, int((time.perf_counter() - started) * 1000))
    return {
        "check_id": check.check_id,
        "required": check.required,
        "passed": passed,
        "reason_code": reason_code,
        "duration_ms": duration_ms,
        "exit_code": exit_code,
    }


def gate_config_invalid() -> DomainError:
    return DomainError(
        code="gate_config_invalid",
        message="Gate configuration is invalid.",
        retryable=True,
    )
