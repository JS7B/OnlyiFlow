# OnlyiFlow

[简体中文](README.zh-CN.md) | English

OnlyiFlow is a small personal development-flow plugin for one owner working across Codex, Claude
Code, and ZCode.

Its portable product boundary is intentionally narrow:

```text
one explicitly invoked Skill
one deterministic local stdio MCP server
local SQLite flow and gate state
```

The host coding agent remains responsible for understanding, planning, editing, debugging, and
testing code. OnlyiFlow records explicit workflow state and deterministic landing evidence. It does
not install Hooks, intercept Agent events, manage Agent configuration, run a background process, or
claim control over direct Git commands.

## Current Status

Version `0.1.0` remains the verified GitHub release. The `0.2.0` release candidate keeps the same
workflow runtime and adds a local Claude Marketplace for persistent `user`-scope installation
across projects on one Windows account. The accepted candidate is committed to `main`, but it is
not tagged or released until separate owner approval.

The Claude installation requires Python 3.11 or newer, the dependencies declared in
`requirements.txt`, and a retained extracted local Marketplace directory. It is not
environment-free, cross-computer setup, an npm package, or a public Marketplace publication.
Multiple active flows remain out of scope.

Claude and Codex pass the complete activation, efficiency/Gate, and release-smoke contracts. The
owner-assisted ZCode smoke passes the same ordinary-isolation, owner-confirmed initialization,
quick-flow, failing/passing Gate, landing, and unload semantics.
No OnlyiFlow plugin, Skill, MCP exposure, versioned cache file, temporary workspace, or runtime
process remains. ZCode intentionally retains only the owner-added uninstalled local marketplace
source, shown in Discover with a `获取` action.

The complete 15-criterion audit and accepted report hashes are recorded in the release-readiness
evidence. The owner authorized this GitHub release on 2026-07-17; no public plugin-marketplace
publication is included.

Do not import the repository source root directly:
host discovery differs, so isolated candidates are generated under `build/loader-candidates/` by
`scripts/build_loader_candidates.py`.

Legacy repositories outside this source tree are reference material only. This repository does not
inherit their adapter, Hook, Attention, event-ingestion, or capability-probe architecture.

## Runtime Requirements

OnlyiFlow does not require a particular environment manager or environment name. Select any Python
3.11+ environment and make sure its `python` command is visible to the host process. If using
Conda, choose and activate the environment yourself before installing dependencies and starting the
host.

The required packages are listed in `requirements.txt`. From a source checkout, install them into
the selected environment with:

```powershell
python -m pip install -r requirements.txt
```

For the Claude release archive, use the copy bundled inside the retained Marketplace directory:

```powershell
python -m pip install -r "<retained-claude-marketplace>\plugins\onlyiflow\requirements.txt"
```

## Repository Layers

Normative specification:

- `docs/product-spec.md`: product behavior and non-goals;
- `docs/engineering-spec.md`: runtime, persistence, transport, packaging, and testing contracts;
- `docs/release-guide.md`: owner installation, verification, cleanup, and approval procedure.

Product and packaging implementation:

- `src/onlyiflow/` and `server/stdio.py`: shipped deterministic runtime;
- `packaging/`: host manifests and manual-only Skill wrapper templates;
- `scripts/build_loader_candidates.py`: generated host packages.

Verification tooling:

- `tests/`: deterministic unit, contract, packaging, and runner tests;
- `scripts/run_skill_evaluations.py`, `scripts/run_efficiency_measurements.py`, and
  `scripts/run_release_smoke.py`: release-evidence runners that are not copied into plugins.

Evidence and history:

- `docs/research/`, `docs/plans/`, and `docs/evaluations/`: observations, execution history, and
  accepted report references;
- ignored JSON reports under `build/task*-*-results/`: local reproducible evidence artifacts.

Task numbers, machine observations, probes, and historical failures in the evidence layer are not
product requirements. When evidence and a normative specification differ, the normative product
and engineering specifications control.

## Documents

- [Product specification](docs/product-spec.md)
- [Engineering specification](docs/engineering-spec.md)
- [Three-host loader research contract](docs/research/2026-07-16-three-host-loader-contract.md)
- [Plugin-first foundation plan](docs/plans/2026-07-16-plugin-first-framework-foundation.md)
- [Owner installation and release guide](docs/release-guide.md)
- [Claude user-scope installation plan](docs/plans/2026-07-18-v0.2.0-claude-user-install.md)

Generated plugin candidates:

- `build/loader-candidates/codex-marketplace/`
- `build/loader-candidates/claude-marketplace/`
- `build/loader-candidates/zcode/` (ZCode local marketplace root; plugin under `onlyiflow/`)

## Core Product Rule

> The host agent owns implementation. OnlyiFlow owns explicit workflow state and deterministic
> landing evidence.

Without external branch protection, CI, or an owner-installed Git hook, OnlyiFlow cannot prevent an
agent or user from running `git push`, `git merge`, or another landing command directly.
