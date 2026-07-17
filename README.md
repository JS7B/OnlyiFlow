# OnlyiFlow

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

Version `0.1.0` is a verified release candidate awaiting separate owner approval to commit, push,
or release. It contains the explicit-only `onlyiflow` Skill wrappers, bundled deterministic
runtime, project-local SQLite state, configured Gate execution, and exactly seven MCP tools with
closed input and output schemas.

Claude and Codex pass the complete activation, efficiency/Gate, and release-smoke contracts. The
owner-assisted ZCode smoke passes the same ordinary-isolation, owner-confirmed initialization,
quick-flow, failing/passing Gate, landing, and unload semantics.
No OnlyiFlow plugin, Skill, MCP exposure, versioned cache file, temporary workspace, or runtime
process remains. ZCode intentionally retains only the owner-added uninstalled local marketplace
source, shown in Discover with a `获取` action.

The complete 15-criterion audit and accepted report hashes are recorded in the release-readiness
evidence. Passing evidence does not itself authorize a commit, push, or release.

Do not import the repository source root directly:
host discovery differs, so isolated candidates are generated under `build/loader-candidates/` by
`scripts/build_loader_candidates.py`.

Legacy repositories outside this source tree are reference material only. This repository does not
inherit their adapter, Hook, Attention, event-ingestion, or capability-probe architecture.

## Repository Layers

Normative specification:

- `docs/product-spec.md`: product behavior and non-goals;
- `docs/engineering-spec.md`: runtime, persistence, transport, packaging, and testing contracts;
- `docs/release-guide.md`: owner installation, verification, cleanup, and approval procedure.

Product and packaging implementation:

- `src/onlyiflow/` and `server/stdio.py`: shipped deterministic runtime;
- `skills/` and `skills-claude/`: shipped manual-only host wrappers;
- host manifests plus `scripts/build_loader_candidates.py`: generated host packages.

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

Generated plugin candidates:

- `build/loader-candidates/codex-marketplace/`
- `build/loader-candidates/claude/onlyiflow/`
- `build/loader-candidates/zcode/` (ZCode local marketplace root; plugin under `onlyiflow/`)

## Core Product Rule

> The host agent owns implementation. OnlyiFlow owns explicit workflow state and deterministic
> landing evidence.

Without external branch protection, CI, or an owner-installed Git hook, OnlyiFlow cannot prevent an
agent or user from running `git push`, `git merge`, or another landing command directly.
