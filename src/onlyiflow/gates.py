from __future__ import annotations

import re
import subprocess
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
    if not raw_checks:
        raise DomainError(
            code="gate_checks_missing",
            message="No gate checks are configured.",
            retryable=True,
        )
    if len(raw_checks) > MAX_CHECKS:
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
        completed = subprocess.run(
            check.command,
            cwd=project_root,
            shell=False,
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
