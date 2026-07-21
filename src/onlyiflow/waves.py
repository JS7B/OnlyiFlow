"""校验版本化 Wave 计划、工作包契约与紧凑交接信息。"""

from __future__ import annotations

import re
from pathlib import PurePosixPath, PureWindowsPath

from .contracts import DomainError


PACKAGE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
PACKAGE_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
REASON_CODE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_]{0,63}$")
CHECK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{7,64}$")
MAX_PACKAGES = 32
MAX_LIST_ITEMS = 32
MAX_TEXT_LENGTH = 1000
MAX_PATH_LENGTH = 512
PACKAGE_STATUSES = [
    "proposed",
    "ready",
    "running",
    "submitted",
    "changes_requested",
    "accepted",
    "integrated",
    "blocked",
    "deferred",
    "superseded",
]
PACKAGE_ACTIONS = {
    "start",
    "submit",
    "request_changes",
    "accept",
    "integrate",
    "interrupt",
    "block",
    "resume",
    "defer",
}
AUTHORIZATIONS = {
    "dependency_install",
    "external_network",
    "external_write",
    "destructive_action",
    "git_commit",
    "git_merge",
    "git_push",
    "release",
}


def validate_flow_mode(mode: str) -> str:
    if mode not in {"direct", "wave"}:
        raise DomainError(
            code="flow_mode_invalid",
            message="Flow mode must be direct or wave.",
            retryable=True,
        )
    return mode


def validate_package_id(package_id: str) -> str:
    if not isinstance(package_id, str) or not PACKAGE_ID_PATTERN.fullmatch(package_id):
        raise DomainError(
            code="package_id_invalid",
            message="Work package ID is invalid.",
            retryable=True,
        )
    return package_id


def normalize_packages(raw_packages: list[dict]) -> list[dict]:
    if (
        not isinstance(raw_packages, list)
        or not raw_packages
        or len(raw_packages) > MAX_PACKAGES
    ):
        raise plan_error(
            "wave_plan_invalid", "Wave plan must contain one to 32 packages."
        )

    packages = [normalize_package(raw) for raw in raw_packages]
    ids = [package["id"] for package in packages]
    slugs = [package["slug"] for package in packages]
    if len({value.casefold() for value in ids}) != len(ids):
        raise plan_error("package_id_duplicate", "Work package IDs must be unique.")
    if len(set(slugs)) != len(slugs):
        raise plan_error("package_slug_duplicate", "Work package slugs must be unique.")

    by_id = {package["id"]: package for package in packages}
    for package in packages:
        for dependency in package["dependencies"]:
            if dependency not in by_id:
                raise plan_error(
                    "package_dependency_missing",
                    "Every work package dependency must exist in the submitted plan.",
                )
            if dependency == package["id"]:
                raise plan_error(
                    "package_dependency_cycle",
                    "A work package cannot depend on itself.",
                )

    ensure_acyclic(packages)
    for package in packages:
        for dependency in package["dependencies"]:
            if by_id[dependency]["wave"] >= package["wave"]:
                raise plan_error(
                    "package_wave_invalid",
                    "A dependency must be assigned to an earlier Wave.",
                )

    for index, package in enumerate(packages):
        for other in packages[index + 1 :]:
            if package["wave"] != other["wave"]:
                continue
            if any(
                scopes_overlap(left, right)
                for left in package["allowed_paths"]
                for right in other["allowed_paths"]
            ):
                raise plan_error(
                    "package_scope_conflict",
                    "Work packages in the same Wave must have disjoint allowed paths.",
                )

    return packages


def normalize_package(raw: dict) -> dict:
    required = {
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
    }
    if not isinstance(raw, dict) or set(raw) != required:
        raise plan_error(
            "wave_plan_invalid",
            "Every work package must use the complete closed contract.",
        )

    package_id = validate_package_id(raw["id"])
    slug = raw["slug"]
    if not isinstance(slug, str) or not PACKAGE_SLUG_PATTERN.fullmatch(slug):
        raise plan_error("package_slug_invalid", "Work package slug is invalid.")
    wave = raw["wave"]
    if not isinstance(wave, int) or isinstance(wave, bool) or not 0 <= wave < 32:
        raise plan_error(
            "package_wave_invalid", "Work package Wave must be from 0 to 31."
        )
    review = raw["requires_independent_review"]
    if not isinstance(review, bool):
        raise plan_error(
            "wave_plan_invalid",
            "requires_independent_review must be a boolean.",
        )

    dependencies = normalize_identifiers(raw["dependencies"], allow_empty=True)
    allowed = normalize_scopes(raw["allowed_paths"], allow_empty=False)
    forbidden = normalize_scopes(raw["forbidden_paths"], allow_empty=True)

    authorizations = normalize_identifiers(
        raw["requires_authorization"], allow_empty=True
    )
    if any(value not in AUTHORIZATIONS for value in authorizations):
        raise plan_error(
            "package_authorization_invalid",
            "Work package authorization requirement is invalid.",
        )

    condition = raw["condition"]
    if condition is not None:
        if not isinstance(condition, dict) or set(condition) != {
            "evidence",
            "on_false",
        }:
            raise plan_error(
                "package_condition_invalid", "Package condition is invalid."
            )
        if condition["on_false"] != "deferred":
            raise plan_error(
                "package_condition_invalid",
                "A false package condition must result in deferred.",
            )
        condition = {
            "evidence": normalize_text(condition["evidence"], "condition evidence"),
            "on_false": "deferred",
        }

    return {
        "id": package_id,
        "slug": slug,
        "title": normalize_text(raw["title"], "package title", maximum=200),
        "purpose": normalize_text(raw["purpose"], "package purpose"),
        "baseline_assumptions": normalize_text_list(
            raw["baseline_assumptions"], allow_empty=False
        ),
        "wave": wave,
        "dependencies": dependencies,
        "allowed_paths": allowed,
        "forbidden_paths": forbidden,
        "deliverables": normalize_text_list(raw["deliverables"], allow_empty=False),
        "non_goals": normalize_text_list(raw["non_goals"], allow_empty=False),
        "acceptance": normalize_text_list(raw["acceptance"], allow_empty=False),
        "check_ids": normalize_check_ids(raw["check_ids"]),
        "runtime_boundaries": normalize_text_list(
            raw["runtime_boundaries"], allow_empty=False
        ),
        "requires_authorization": authorizations,
        "requires_independent_review": review,
        "condition": condition,
    }


def normalize_record(
    *,
    action: str,
    base_commit: str | None,
    head_commit: str | None,
    changed_files: list[str] | None,
    checks: list[dict] | None,
    known_limits: list[str] | None,
    reason_code: str | None,
    retryable: bool | None,
) -> dict:
    if action not in PACKAGE_ACTIONS:
        raise action_error("package_action_invalid", "Package action is invalid.")

    values = {
        "base_commit": base_commit,
        "head_commit": head_commit,
        "changed_files": changed_files,
        "checks": checks,
        "known_limits": known_limits,
        "reason_code": reason_code,
        "retryable": retryable,
    }
    # 每种操作都有封闭的证据结构，任何无关字段都会被拒绝。
    required: dict[str, set[str]] = {
        "start": set(),
        "submit": {
            "base_commit",
            "head_commit",
            "changed_files",
            "checks",
            "known_limits",
        },
        "request_changes": {"reason_code"},
        "accept": set(),
        "integrate": {"head_commit"},
        "interrupt": {"reason_code", "retryable"},
        "block": {"reason_code"},
        "resume": {"reason_code"},
        "defer": {"reason_code"},
    }
    allowed = {name: set(fields) for name, fields in required.items()}
    allowed["interrupt"].update({"base_commit", "head_commit", "changed_files"})
    supplied = {key for key, value in values.items() if value is not None}
    if not required[action] <= supplied or not supplied <= allowed[action]:
        raise action_error(
            "package_action_fields_invalid",
            "Package action fields do not match the selected action.",
        )

    normalized: dict = {"action": action}
    if base_commit is not None:
        normalized["base_commit"] = normalize_commit(base_commit)
    if head_commit is not None:
        normalized["head_commit"] = normalize_commit(head_commit)
    if changed_files is not None:
        normalized["changed_files"] = normalize_changed_files(changed_files)
    if checks is not None:
        normalized["checks"] = normalize_checks(checks)
    if known_limits is not None:
        try:
            normalized["known_limits"] = normalize_text_list(
                known_limits, allow_empty=True, maximum_items=8, maximum_text=500
            )
        except DomainError:
            raise action_error(
                "package_known_limits_invalid",
                "Package known limits are invalid.",
            ) from None
    if reason_code is not None:
        if not isinstance(reason_code, str) or not REASON_CODE_PATTERN.fullmatch(
            reason_code
        ):
            raise action_error("reason_code_invalid", "Reason code is invalid.")
        normalized["reason_code"] = reason_code
    if retryable is not None:
        if not isinstance(retryable, bool):
            raise action_error(
                "package_action_fields_invalid", "retryable must be boolean."
            )
        normalized["retryable"] = retryable
    return normalized


def changed_files_in_scope(changed_files: list[str], package: dict) -> bool:
    # 这些路径由宿主声明，仅依据已确认的工作包契约进行校验。
    return all(
        any(path_in_scope(path, scope) for scope in package["allowed_paths"])
        and not any(path_in_scope(path, scope) for scope in package["forbidden_paths"])
        for path in changed_files
    )


def contract_equal(left: dict, right: dict) -> bool:
    return left == right


def normalize_text(value: object, label: str, *, maximum: int = MAX_TEXT_LENGTH) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise plan_error("wave_plan_invalid", f"{label.capitalize()} is invalid.")
    return value.strip()


def normalize_text_list(
    values: object,
    *,
    allow_empty: bool,
    maximum_items: int = MAX_LIST_ITEMS,
    maximum_text: int = MAX_TEXT_LENGTH,
) -> list[str]:
    if not isinstance(values, list) or len(values) > maximum_items:
        raise plan_error("wave_plan_invalid", "A work package list is invalid.")
    if not allow_empty and not values:
        raise plan_error("wave_plan_invalid", "A required work package list is empty.")
    normalized = [
        normalize_text(value, "list value", maximum=maximum_text) for value in values
    ]
    if len({value.casefold() for value in normalized}) != len(normalized):
        raise plan_error(
            "wave_plan_invalid", "Work package list values must be unique."
        )
    return normalized


def normalize_identifiers(values: object, *, allow_empty: bool) -> list[str]:
    if not isinstance(values, list) or len(values) > MAX_PACKAGES:
        raise plan_error("wave_plan_invalid", "Work package identifiers are invalid.")
    if not allow_empty and not values:
        raise plan_error("wave_plan_invalid", "Work package identifiers are required.")
    normalized = []
    for value in values:
        if not isinstance(value, str) or not PACKAGE_ID_PATTERN.fullmatch(value):
            raise plan_error("package_id_invalid", "Work package ID is invalid.")
        normalized.append(value)
    if len({value.casefold() for value in normalized}) != len(normalized):
        raise plan_error(
            "wave_plan_invalid", "Work package identifiers must be unique."
        )
    return normalized


def normalize_scopes(values: object, *, allow_empty: bool) -> list[str]:
    if not isinstance(values, list) or len(values) > MAX_LIST_ITEMS:
        raise plan_error("package_scope_invalid", "Package path scope is invalid.")
    if not allow_empty and not values:
        raise plan_error("package_scope_invalid", "Package allowed paths are required.")
    normalized = [normalize_scope(value) for value in values]
    if len({value.casefold() for value in normalized}) != len(normalized):
        raise plan_error("package_scope_invalid", "Package path scopes must be unique.")
    return normalized


def normalize_scope(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise plan_error("package_scope_invalid", "Package path scope is invalid.")
    candidate = value.strip().replace("\\", "/")
    is_directory = candidate.endswith("/")
    raw = candidate[:-1] if is_directory else candidate
    if not raw or len(candidate) > MAX_PATH_LENGTH:
        raise plan_error("package_scope_invalid", "Package path scope is invalid.")
    posix = PurePosixPath(raw)
    windows = PureWindowsPath(raw)
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or any(part in {"", ".", ".."} for part in posix.parts)
    ):
        raise plan_error(
            "package_scope_invalid",
            "Package path scopes must be project-relative.",
        )
    return posix.as_posix() + ("/" if is_directory else "")


def normalize_changed_files(values: object) -> list[str]:
    try:
        scopes = normalize_scopes(values, allow_empty=False)
    except DomainError:
        raise action_error(
            "package_changed_files_invalid",
            "Changed files must identify exact project-relative files.",
        ) from None
    if any(value.endswith("/") for value in scopes):
        raise action_error(
            "package_changed_files_invalid",
            "Changed files must identify exact project-relative files.",
        )
    return scopes


def normalize_checks(values: object) -> list[dict]:
    if not isinstance(values, list) or not values or len(values) > 32:
        raise action_error("package_checks_invalid", "Package checks are invalid.")
    normalized = []
    seen = set()
    for raw in values:
        if not isinstance(raw, dict) or set(raw) != {
            "check_id",
            "passed",
            "reason_code",
        }:
            raise action_error("package_checks_invalid", "Package checks are invalid.")
        check_id = raw["check_id"]
        reason = raw["reason_code"]
        if (
            not isinstance(check_id, str)
            or not CHECK_ID_PATTERN.fullmatch(check_id)
            or check_id in seen
            or not isinstance(raw["passed"], bool)
            or not isinstance(reason, str)
            or not REASON_CODE_PATTERN.fullmatch(reason)
        ):
            raise action_error("package_checks_invalid", "Package checks are invalid.")
        seen.add(check_id)
        normalized.append(
            {
                "check_id": check_id,
                "passed": raw["passed"],
                "reason_code": reason,
            }
        )
    return normalized


def normalize_check_ids(values: object) -> list[str]:
    if not isinstance(values, list) or not values or len(values) > MAX_LIST_ITEMS:
        raise plan_error("package_check_ids_invalid", "Package check IDs are invalid.")
    if any(
        not isinstance(value, str) or not CHECK_ID_PATTERN.fullmatch(value)
        for value in values
    ):
        raise plan_error("package_check_ids_invalid", "Package check IDs are invalid.")
    if len({value.casefold() for value in values}) != len(values):
        raise plan_error(
            "package_check_ids_invalid", "Package check IDs must be unique."
        )
    return values


def normalize_commit(value: object) -> str:
    if not isinstance(value, str) or not COMMIT_PATTERN.fullmatch(value):
        raise action_error("package_commit_invalid", "Package commit is invalid.")
    return value


def ensure_acyclic(packages: list[dict]) -> None:
    graph = {package["id"]: package["dependencies"] for package in packages}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(package_id: str) -> None:
        if package_id in visiting:
            raise plan_error(
                "package_dependency_cycle", "Work package DAG has a cycle."
            )
        if package_id in visited:
            return
        visiting.add(package_id)
        for dependency in graph[package_id]:
            visit(dependency)
        visiting.remove(package_id)
        visited.add(package_id)

    for package_id in graph:
        visit(package_id)


def scopes_overlap(left: str, right: str) -> bool:
    # 末尾斜杠表示目录范围，其余值表示精确文件。
    left_dir = left.endswith("/")
    right_dir = right.endswith("/")
    left_value = left[:-1] if left_dir else left
    right_value = right[:-1] if right_dir else right
    if not left_dir and not right_dir:
        return left_value.casefold() == right_value.casefold()
    if left_dir and right_dir:
        left_prefix = left_value.casefold() + "/"
        right_prefix = right_value.casefold() + "/"
        return left_prefix.startswith(right_prefix) or right_prefix.startswith(
            left_prefix
        )
    directory = left_value if left_dir else right_value
    file_path = right_value if left_dir else left_value
    return file_path.casefold().startswith(directory.casefold() + "/")


def path_in_scope(path: str, scope: str) -> bool:
    if scope.endswith("/"):
        return path.casefold().startswith(scope.casefold())
    return path.casefold() == scope.casefold()


def plan_error(code: str, message: str) -> DomainError:
    return DomainError(
        code=code,
        message=message,
        retryable=True,
        next_action={"tool": "wave_plan_set", "reason_code": "revise_wave_plan"},
    )


def action_error(code: str, message: str) -> DomainError:
    return DomainError(
        code=code,
        message=message,
        retryable=True,
        next_action={
            "tool": "work_package_status",
            "reason_code": "refresh_package_state",
        },
    )
