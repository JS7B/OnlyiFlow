from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = REPOSITORY_ROOT / "packaging"
COMMON_DIRECTORIES = ("server", "src")
COMMON_FILES = ("pyproject.toml", "requirements.txt")
HOST_TEMPLATE_ROOTS = {
    "codex": TEMPLATE_ROOT / "codex",
    "claude": TEMPLATE_ROOT / "claude",
    "zcode": TEMPLATE_ROOT / "zcode",
}
SHARED_HOST_DIRECTORIES = {
    "claude": (TEMPLATE_ROOT / "shared" / "skills-claude",),
    "zcode": (TEMPLATE_ROOT / "shared" / "skills-claude",),
}


def build_candidates(output_root: Path) -> dict[str, Path]:
    output_root = output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"Candidate output already exists: {output_root}")

    roots = {
        "codex": output_root / "codex-marketplace" / "plugins" / "onlyiflow",
        "claude": output_root / "claude-marketplace" / "plugins" / "onlyiflow",
        "zcode": output_root / "zcode" / "onlyiflow",
    }
    for host, destination in roots.items():
        destination.mkdir(parents=True)
        for directory in COMMON_DIRECTORIES:
            shutil.copytree(
                REPOSITORY_ROOT / directory,
                destination / directory,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        for filename in COMMON_FILES:
            shutil.copy2(REPOSITORY_ROOT / filename, destination / filename)
        copy_template_root(HOST_TEMPLATE_ROOTS[host], destination)
        for directory in SHARED_HOST_DIRECTORIES.get(host, ()):
            shutil.copytree(
                directory,
                destination / directory.name,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )

    write_codex_marketplace(output_root / "codex-marketplace")
    write_claude_marketplace(output_root / "claude-marketplace")
    write_zcode_marketplace(output_root / "zcode")
    return roots


def copy_template_root(source: Path, destination: Path) -> None:
    for entry in source.iterdir():
        target = destination / entry.name
        if entry.is_dir():
            shutil.copytree(
                entry,
                target,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        else:
            shutil.copy2(entry, target)


def write_codex_marketplace(marketplace_root: Path) -> None:
    metadata = marketplace_root / ".agents" / "plugins" / "marketplace.json"
    metadata.parent.mkdir(parents=True)
    payload = {
        "name": "onlyiflow-dev",
        "interface": {"displayName": "OnlyiFlow Development"},
        "plugins": [
            {
                "name": "onlyiflow",
                "source": {"source": "local", "path": "./plugins/onlyiflow"},
                "policy": {
                    "installation": "AVAILABLE",
                    "authentication": "ON_INSTALL",
                },
                "category": "Productivity",
            }
        ],
    }
    metadata.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_claude_marketplace(marketplace_root: Path) -> None:
    plugin = json.loads(
        (marketplace_root / "plugins/onlyiflow/.claude-plugin/plugin.json").read_text(
            encoding="utf-8"
        )
    )
    metadata = marketplace_root / ".claude-plugin" / "marketplace.json"
    metadata.parent.mkdir(parents=True)
    payload = {
        "name": "onlyiflow-local",
        "owner": {"name": "OnlyiFlow"},
        "description": "Local user-scope distribution for OnlyiFlow.",
        "plugins": [
            {
                "name": plugin["name"],
                "source": "./plugins/onlyiflow",
                "version": plugin["version"],
                "strict": True,
            }
        ],
    }
    metadata.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_zcode_marketplace(marketplace_root: Path) -> None:
    plugin = json.loads(
        (marketplace_root / "onlyiflow/.zcode-plugin/plugin.json").read_text(
            encoding="utf-8"
        )
    )
    payload = {
        "name": "onlyiflow-dev",
        "plugins": [
            {
                "name": plugin["name"],
                "version": plugin["version"],
                "description": plugin["description"],
                "source": "./onlyiflow",
            }
        ],
    }
    (marketplace_root / "marketplace.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build isolated Codex, Claude Code, and ZCode plugin candidates."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPOSITORY_ROOT / "build" / "loader-candidates",
    )
    args = parser.parse_args()
    roots = build_candidates(args.output_root)
    for host, root in roots.items():
        print(f"{host}: {root}")


if __name__ == "__main__":
    main()
