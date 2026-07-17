from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from .contracts import DomainError


INITIALIZATION_ENTRIES = [
    ".onlyiflow/onlyiflow.db",
    ".onlyiflow/config.toml",
    ".onlyiflow/specs/",
]
MAX_EXPECTED_FILES = 100
MAX_EXPECTED_FILE_LENGTH = 512


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    state_root: Path
    database: Path
    config: Path
    specs: Path

    @classmethod
    def from_root(cls, root: Path) -> ProjectPaths:
        state_root = root / ".onlyiflow"
        return cls(
            root=root,
            state_root=state_root,
            database=state_root / "onlyiflow.db",
            config=state_root / "config.toml",
            specs=state_root / "specs",
        )

    def is_managed(self) -> bool:
        return self.database.is_file() and self.config.is_file() and self.specs.is_dir()


def resolve_project_root(project_root: str) -> ProjectPaths:
    if not isinstance(project_root, str) or not project_root.strip():
        raise DomainError(
            code="project_root_required",
            message="Project root is required.",
            retryable=True,
        )

    try:
        root = Path(project_root.strip()).expanduser().resolve(strict=True)
    except OSError as error:
        raise DomainError(
            code="project_root_not_found",
            message="Project root does not exist.",
            retryable=True,
        ) from error

    if not root.is_dir():
        raise DomainError(
            code="project_root_not_directory",
            message="Project root must be a directory.",
            retryable=True,
        )
    return ProjectPaths.from_root(root)


def normalize_expected_files(expected_files: list[str]) -> list[str]:
    if (
        not isinstance(expected_files, list)
        or not expected_files
        or len(expected_files) > MAX_EXPECTED_FILES
    ):
        raise expected_files_error()

    normalized: list[str] = []
    seen: set[str] = set()
    for value in expected_files:
        if (
            not isinstance(value, str)
            or not value.strip()
            or len(value.strip()) > MAX_EXPECTED_FILE_LENGTH
        ):
            raise expected_files_error()

        candidate = value.strip().replace("\\", "/")
        posix = PurePosixPath(candidate)
        windows = PureWindowsPath(candidate)
        if (
            posix.is_absolute()
            or windows.is_absolute()
            or windows.drive
            or any(part in {"", ".", ".."} for part in posix.parts)
        ):
            raise expected_files_error()

        relative = posix.as_posix()
        key = relative.casefold()
        if key in seen:
            raise expected_files_error()
        seen.add(key)
        normalized.append(relative)
    return normalized


def expected_files_error() -> DomainError:
    return DomainError(
        code="expected_files_invalid",
        message="Expected files must be unique project-relative paths.",
        retryable=True,
    )
