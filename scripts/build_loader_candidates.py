from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMMON_DIRECTORIES = ("server", "src")
COMMON_FILES = ("pyproject.toml",)
HOST_CONTENTS = {
    "codex": {
        "directories": (".codex-plugin", "skills"),
        "files": (".mcp.json",),
    },
    "claude": {
        "directories": (".claude-plugin", "skills-claude"),
        "files": (".mcp.claude.json",),
    },
    "zcode": {
        "directories": (".zcode-plugin", "skills-claude"),
        "files": (),
    },
}


def build_candidates(output_root: Path) -> dict[str, Path]:
    output_root = output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"Candidate output already exists: {output_root}")

    roots = {
        "codex": output_root / "codex-marketplace" / "plugins" / "onlyiflow",
        "claude": output_root / "claude" / "onlyiflow",
        "zcode": output_root / "zcode" / "onlyiflow",
    }
    for host, destination in roots.items():
        destination.mkdir(parents=True)
        for directory in COMMON_DIRECTORIES + HOST_CONTENTS[host]["directories"]:
            shutil.copytree(
                REPOSITORY_ROOT / directory,
                destination / directory,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        for filename in HOST_CONTENTS[host]["files"]:
            shutil.copy2(REPOSITORY_ROOT / filename, destination / filename)
        for filename in COMMON_FILES:
            shutil.copy2(REPOSITORY_ROOT / filename, destination / filename)

    write_codex_marketplace(output_root / "codex-marketplace")
    write_zcode_marketplace(output_root / "zcode")
    return roots


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
