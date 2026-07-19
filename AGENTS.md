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

Version `0.3.0` is the current verified GitHub release. It includes the Claude Code user-scope
installation introduced in 0.2.0 plus owner-confirmed Gate configuration, project readiness, and
the legacy empty-Gate migration path. The normative product, engineering, and release contracts
are in `docs/product-spec.md`, `docs/engineering-spec.md`, and
`docs/release-guide.md`. The accepted `0.1.0` audit and delivery record are in
`docs/evaluations/2026-07-17-task7-release-readiness.md`; the `0.2.0` installation evidence is in
`docs/evaluations/2026-07-18-v0.2.0-claude-user-install.md`; and the local plus Claude acceptance
record for the `0.3.0` release is in
`docs/evaluations/2026-07-19-v0.3.0-gate-configuration.md`. The owner deferred live Codex 0.3.0
model verification. The retained local Codex installation now resolves to 0.3.0 from the generated
Marketplace and remains enabled, but its host inventory is not accepted as model-visibility
evidence. ZCode 3.3.6 owner-assisted 0.3.0 verification passed through unload and cleanup; the
uninstalled local Marketplace remains the only retained ZCode discovery state.

Claude 0.3.0 additionally passed the corrected 12-check release smoke, including separate Gate
proposal and owner-confirmation sessions with the exact `project_status -> gate_configure`
confirmation sequence. The accepted report and hash are recorded in the 0.3.0 evidence document.
ZCode 0.3.0 also passed the owner-assisted eight-tool confirmation, failing/passing Gate, landing,
unload, and cleanup sequence recorded there.

No runner-owned OnlyiFlow test plugin, MCP registration, versioned plugin cache, temporary
workspace, or runtime process may remain after verification. The owner-retained Codex development
installation and the owner-approved uninstalled ZCode Discover source are the only retained
lifecycle state. A successful host listing is not model-visibility evidence; accepted reports must
contain the expected real MCP call sequence.

The owner-rejected commit `8a539f2b8d1debb34b184f4682910ff30dbf863a` remains in Git history
only. Corrective merge `0305d9e5c9bc0491bc30e5e25b72cf1097a6e068` recorded it without
changing the validated release tree. Do not install another Codex version, publish OnlyiFlow to a
public plugin marketplace, or start later product work without explicit owner direction.

Claude user-scope installation requires a retained extracted local Marketplace directory plus a
user-selected Python 3.11+ environment containing the dependencies listed in `requirements.txt`.
Host launchers call the `python` command visible to their process and must not name a Conda
environment. Claude Code 2.1.197 was observed returning `Unknown command` when the installed
directory Marketplace source was hidden. Do not claim environment-free or source-independent
installation, add a frozen runtime, publish through npm, or implement multiple active flows.

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

The implementation layout is:

```text
packaging/codex/.codex-plugin/plugin.json
packaging/codex/.mcp.json
packaging/codex/skills/onlyiflow/SKILL.md
packaging/claude/.claude-plugin/plugin.json
packaging/claude/.mcp.claude.json
packaging/zcode/.zcode-plugin/plugin.json
packaging/shared/skills-claude/onlyiflow/SKILL.md
pyproject.toml
requirements.txt
server/stdio.py
src/onlyiflow/
scripts/build_loader_candidates.py
tests/
docs/
```

Generated development roots are:

```text
build/loader-candidates/codex-marketplace/plugins/onlyiflow/
build/loader-candidates/claude-marketplace/plugins/onlyiflow/
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

The current release exposes exactly these eight tools:

```text
project_status
project_init
gate_configure
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

After initialization, `project_status` reports Gate readiness. When no flow is active, an empty
configuration returns `gate_configure` as the one next action and `flow_start` must reject the
project. The Skill must present the complete proposed checks and wait for a separate owner turn;
only after confirmation may `gate_configure` atomically replace the complete list. Configuration
replacement is forbidden while any flow is active. A flow created by an earlier version with an
empty Gate is the sole exception: `project_status` returns `gate_configure`, and a separately
confirmed call may write its first non-empty Gate before the flow resumes.

For an already managed and Gate-configured project, a new `quick` flow must reach `implementing`
through:

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
and exit code where applicable. Gate configuration responses add only check IDs, required flags,
timeouts, and counts. Command text exists only in `config.toml`, never in SQLite, domain events,
MCP responses, or reports.

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
claude plugin validate build\loader-candidates\claude-marketplace\plugins\onlyiflow
claude plugin validate build\loader-candidates\claude-marketplace
conda run --no-capture-output -n myself python -s -B scripts\run_claude_user_install_lifecycle.py --timeout-seconds 600
conda run --no-capture-output -n myself python -s -B scripts\run_claude_user_install_acceptance.py --timeout-seconds 600
```

These commands use the owner's preferred local development environment only; that environment name
is not part of the distributed launcher or user installation contract.

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
