# AGENTS.md

## Scope

These instructions apply to the entire repository.

Repository and product name: `OnlyiFlow`.

This directory is a greenfield repository. Any legacy repository outside this source tree is
reference material only. Do not merge, cherry-pick, copy directories, or preserve APIs merely
because they exist in an older repository. Reuse an idea only when the current product and
engineering specifications explicitly approve it and a focused test justifies the implementation.

## Owner And Environment

- The owner is an AI full-stack developer.
- The preferred Python environment is the Anaconda environment named `myself`.
- Target Python 3.11 or newer.
- Ask before installing or upgrading any dependency.
- Do not initialize Git, create branches, commit, push, install plugins, or modify user-level Agent
  configuration unless the owner explicitly authorizes that action.

## Current Boundary

Version `0.1.0` is a verified release candidate. The normative product, engineering, and release
contracts are in `docs/product-spec.md`, `docs/engineering-spec.md`, and `docs/release-guide.md`.
The accepted reports, hashes, three-host lifecycle results, and fifteen-criterion audit are in
`docs/evaluations/2026-07-17-task7-release-readiness.md`.

No OnlyiFlow test plugin, MCP registration, versioned plugin cache, temporary workspace, or runtime
process may remain after verification. The owner-approved uninstalled ZCode Discover source is the
only retained lifecycle state. A successful host listing is not model-visibility evidence; accepted
reports must contain the expected real MCP call sequence.

The validated local base is `c57ad88b38e94fbba67d6b2bd561a3feff37adec`. Live `origin/main`
points to owner-rejected commit `8a539f2b8d1debb34b184f4682910ff30dbf863a`, which is intentionally
excluded from this tree. Do not merge it, force-push, commit, push, release, install another Codex
version, or start later product work without explicit owner direction.

The intended first product increment is one manually invoked `onlyiflow` Skill plus one local stdio
MCP server. It must not contain or install Hooks, subagents, commands, background monitors,
adapters, daemons, event collectors, or model-driven orchestration.

## Product Rules

Core rule:

> The host agent owns implementation. OnlyiFlow owns explicit workflow state and deterministic
> landing evidence.

- Ordinary coding requests must not activate OnlyiFlow.
- Only explicit OnlyiFlow requests may load the Skill or call workflow tools.
- `quick` work must reach implementation with minimal ceremony.
- `standard` work may require one compact spec.
- `deep` work requires owner confirmation before additional planning or approval ceremony.
- OnlyiFlow must never claim that a Skill or MCP server prevents direct `git push` or `git merge`.
- Repository enforcement belongs to CI, branch protection, or an owner-installed Git hook outside
  the first plugin increment.
- Human approval must not be exposed as a model-callable MCP tool.

## Greenfield Architecture Rules

Treat the repository root as the source root, not an installable cross-host plugin root. Live proof
showed that Claude Code auto-discovers root `skills/` and project `.mcp.json` in addition to its
declared plugin resources, which duplicates a universal source tree. Generate minimal host package
roots with `scripts/build_loader_candidates.py`; every generated package must remain self-contained.

The proposed implementation layout is:

```text
.codex-plugin/plugin.json
.claude-plugin/plugin.json
.zcode-plugin/plugin.json
skills/onlyiflow/SKILL.md        # Codex wrapper
skills-claude/onlyiflow/SKILL.md # Claude/ZCode manual wrapper until ZCode proof differs
.mcp.json
.mcp.claude.json
pyproject.toml
server/stdio.py
src/onlyiflow/
scripts/build_loader_candidates.py
tests/
docs/
```

Generated development roots are:

```text
build/loader-candidates/codex-marketplace/plugins/onlyiflow/
build/loader-candidates/claude/onlyiflow/
build/loader-candidates/zcode/onlyiflow/
```

The runtime keeps business logic transport-independent:

- `src/onlyiflow/domain.py`: risk levels and explicit state transitions.
- `src/onlyiflow/contracts.py`: shared success/error and tool data contracts.
- `src/onlyiflow/paths.py`: project-root validation and `.onlyiflow/` paths.
- `src/onlyiflow/storage.py`: SQLite schema and repositories.
- `src/onlyiflow/gates.py`: deterministic checks and compact evidence.
- `src/onlyiflow/runtime.py`: the only workflow facade used by MCP.
- `src/onlyiflow/mcp_server.py`: MCP registration and protocol mapping only.
- `server/stdio.py`: plugin-local bootstrap only; no business rules.

Do not create adapter registries, platform capability planners, installation ownership frameworks,
Hook normalization, transcript/event ledgers, Attention loops, or generated Agent configuration.

## MCP Boundary

The first increment exposes exactly these seven tools:

```text
project_status
project_init
flow_start
spec_submit
flow_claim
gate_run
landing_request
```

Every tool must:

- use a closed JSON Schema;
- resolve and validate an explicit project root on every call;
- use explicit flow IDs after flow creation;
- return a stable response with `ok: true` plus `data`, or `ok: false` plus `error`;
- return at most one `next_action`;
- expose structured content plus a serialized JSON text fallback;
- map correctable domain failures to MCP tool-execution errors;
- omit prompts, transcripts, credentials, environment dumps, absolute external paths, commands,
  stdout, and stderr;
- remain deterministic and make no network or model call.

`project_status` must never create `.onlyiflow/`. Only `project_init`, after owner confirmation, may
create local state.

For an already managed project, a new `quick` flow must reach `implementing` through:

```text
project_status -> flow_start
```

`flow_start` therefore owns the atomic quick create-and-claim behavior. Standard and deep flows
remain explicit: create, submit one compact spec, then claim.

The MVP permits at most one non-terminal flow per managed project. Starting another flow must
return a structured conflict instead of guessing which flow is active.

## Persistence And Privacy

Managed projects use:

```text
<project>/.onlyiflow/
  onlyiflow.db
  config.toml
  specs/
```

Do not create attention keys, generated Agent configuration, adapter manifests, event transcripts,
or raw command-output logs.

Gate evidence is compact metadata only: check ID, required flag, pass/fail, reason code, duration,
and exit code where applicable.

## Development Rules

For product-runtime changes:

1. Add a failing test for the requested behavior.
2. Confirm the intended failure.
3. Implement the smallest passing change.
4. Run the targeted test.
5. Run the complete verification suite before completion.

Prefer simple functions and explicit data structures. Do not generalize host packaging before the
loader contract proves a difference that requires it.

Current local verification consists of:

```powershell
conda run --no-capture-output -n myself python -s -B -m unittest discover -s tests -v
conda run --no-capture-output -n myself python -s -B "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" build\loader-candidates\codex-marketplace\plugins\onlyiflow\skills\onlyiflow
claude plugin validate build\loader-candidates\claude\onlyiflow
```

The system `plugin-creator/scripts/validate_plugin.py` currently expects a Claude-style
`mcpServers` wrapper inside `.mcp.json` and rejects Codex's runtime-verified direct server map. Do
not change the working Codex companion file to satisfy that stale preflight. The foundation
contract tests, Codex lifecycle load, exact real MCP calls, and 36-case report are the acceptance
evidence for the Codex candidate.

Expected mentions of prohibited features must appear only in explicit non-goal or historical
context.

## ZCode Boundary

ZCode Desktop folder/marketplace import is the authoritative installation surface for release
acceptance. The locally observed embedded CLI may be used for read-only discovery and automated
preflight, but it must not silently install, enable, disable, or remove the owner's plugins.

Prepare `build/loader-candidates/zcode/` as the owner-imported local marketplace root. Its
`marketplace.json` points only to the self-contained `onlyiflow/` plugin beneath it. Do not ask the
owner to import the single plugin directory or the repository source root.

Do not treat a locally observed `.zcode-plugin/plugin.json` shape as a stable public standard. It
may be used to build a disposable candidate only after the research contract is followed, and the
owner must perform the final UI import and smoke test.
