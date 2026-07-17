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

Tasks 1 through 3 are complete. Task 4's explicit Skill implementation, 10/5/3 evaluation set, and
repeatable host evaluation runner are locally complete. Version `0.1.0` contains the `onlyiflow` Skill
wrappers, the bundled deterministic runtime, project-local SQLite state, configured gate execution,
and exactly seven MCP tools with closed input and output schemas.

Claude's full fresh-session report now passes all 36 enabled/disabled cases with no infrastructure
or cleanup error. Codex remains the Task 4 gate because direct probes confirmed severe WebSocket and
HTTPS transport instability. The owner can rerun the documented Codex command in the
[Task 4 evaluation contract](docs/evaluations/2026-07-16-task4-skill-evaluation.md) when that
connection is stable. ZCode retains the same structurally verified candidate boundary; its live
Desktop import remains an owner-assisted release gate. No test plugin or marketplace remains
installed.

Do not import the repository source root directly:
host discovery differs, so isolated candidates are generated under `build/loader-candidates/` by
`scripts/build_loader_candidates.py`.

The older `D:\AgentX\OnlyiFlow` repository is reference material only. This repository does not
inherit its adapter, Hook, Attention, event-ingestion, or capability-probe architecture.

## Documents

- [Product specification](docs/product-spec.md)
- [Engineering specification](docs/engineering-spec.md)
- [Three-host loader research contract](docs/research/2026-07-16-three-host-loader-contract.md)
- [Plugin-first foundation plan](docs/plans/2026-07-16-plugin-first-framework-foundation.md)

Generated plugin candidates:

- `build/loader-candidates/codex-marketplace/`
- `build/loader-candidates/claude/onlyiflow/`
- `build/loader-candidates/zcode/onlyiflow/`

## Core Product Rule

> The host agent owns implementation. OnlyiFlow owns explicit workflow state and deterministic
> landing evidence.

Without external branch protection, CI, or an owner-installed Git hook, OnlyiFlow cannot prevent an
agent or user from running `git push`, `git merge`, or another landing command directly.
