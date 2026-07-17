# OnlyiFlow Engineering Specification

Date: 2026-07-16

Status: Tasks 1 through 4 complete; Task 5 measurement implementation complete, live evidence pending

## Greenfield Rule

This repository starts from an empty implementation boundary.

`D:\AgentX\OnlyiFlow` may be read to understand prior failures and stable domain ideas, but it is
not a source branch. Do not merge it, cherry-pick it, copy its package directories, or preserve its
unreleased APIs.

Ideas that may be independently reimplemented after tests justify them:

- `quick`, `standard`, and `deep` risk names;
- explicit flow-transition concepts;
- project-local `.onlyiflow/` state;
- SQLite transactions and deterministic gate evidence;
- transport-independent runtime methods.

Do not reuse:

- Agent adapters or registries;
- Hooks or event-ingestion paths;
- Attention/event ledgers and workspace observation collectors;
- platform capability probes and `active` status models;
- configuration ownership, rollback, or safe-uninstall frameworks;
- generated Agent settings;
- old MCP and CLI surface compatibility layers.

## Repository Source And Host Package Roots

The repository is the canonical source root, but it is not itself a safe universal plugin root.
Runtime proof showed that Claude Code auto-discovers root `skills/` and a project `.mcp.json` in
addition to manifest-declared plugin resources. A source tree containing multiple host wrappers
therefore produces duplicate Skill and MCP exposure.

Keep the semantic runtime in one source tree and generate isolated host package roots:

```text
OnlyiFlow_next/
  .codex-plugin/plugin.json
  .claude-plugin/plugin.json
  .zcode-plugin/plugin.json
  skills/onlyiflow/SKILL.md        # Codex wrapper
  skills-claude/onlyiflow/SKILL.md # Claude/ZCode wrapper
  .mcp.json
  .mcp.claude.json
  pyproject.toml
  server/stdio.py
  src/onlyiflow/
  scripts/build_loader_candidates.py
  tests/
  docs/
```

`scripts/build_loader_candidates.py` copies an allowlisted subset into each generated root and
excludes bytecode caches. No installed plugin may depend on the source checkout, a sibling
repository, an editable install, or a path outside its generated plugin root.

Host launch metadata may differ, but all candidates use the same `server/stdio.py` and bundled
runtime. Generated artifacts are tested for isolation and semantic parity and contain no
platform-specific business rules.

## Runtime Layout

Task 2 established the historical minimum skeleton:

```text
src/onlyiflow/
  __init__.py
  mcp_server.py
server/
  stdio.py
```

At that checkpoint `mcp_server.py` registered an empty `FastMCP` server. Task 3 then added each
workflow tool through a failing test.

The current Task 3 runtime is:

```text
src/onlyiflow/
  __init__.py
  contracts.py
  domain.py
  paths.py
  storage.py
  gates.py
  runtime.py
  mcp_server.py
server/
  stdio.py
```

Responsibilities:

- `contracts.py`: shared data contracts and serialization.
- `domain.py`: risk parsing, states, and transitions only.
- `paths.py`: explicit project-root validation and local paths.
- `storage.py`: schema, sessions, and focused repositories.
- `gates.py`: configured process execution and compact evidence.
- `runtime.py`: project, flow, spec, gate, and landing operations.
- `mcp_server.py`: seven tool registrations and MCP error/result mapping.
- `server/stdio.py`: add the plugin-owned `src` directory to import resolution and start stdio.

Do not add new runtime modules unless a focused failing test and a current product requirement
justify the split.

## Python And Dependency Boundary

- Python 3.11+ is the only implementation language in the first increment.
- `pyproject.toml` declares version `0.1.0`, Python `>=3.11`, setuptools, and
  `fastmcp>=3.4,<4`.
- No dependency installation occurs from the Skill, MCP server, launcher, or plugin lifecycle.
- The selected interpreter and dependency availability are loader acceptance facts, not assumptions.
- The loader spike must use the exact final launcher and successfully import the real runtime plus
  every declared third-party dependency.
- A fixed standalone `ping` that bypasses the real import path is not sufficient evidence.

The owner-approved `myself` environment remains the interpreter source. Task 2 was verified with
Python 3.12 and the already-installed FastMCP 3.4 family. No absolute interpreter path or dependency
installation was added.

## Project Root Contract

Every MCP tool accepts an explicit `project_root` string and resolves it on every call.

Validation rules:

- the input must identify an existing directory;
- resolution must not depend on process-wide current-directory state;
- the resolved root is used internally but is not echoed in normal results;
- paths returned in tool data are project-relative;
- unmanaged reads do not create files;
- mutations outside the resolved project root are rejected.

Host-provided project-root variables may help the Skill supply the argument, but no host-specific
variable becomes shared business state.

## Persistence

Managed state:

```text
<project>/.onlyiflow/
  onlyiflow.db
  config.toml
  specs/<flow_id>.json
```

Initial tables:

```text
flows
specs
gates
domain_events
```

No development-event table, transcript table, Attention table, adapter table, or generated Agent
configuration is created.

Use SQLite with foreign keys, a busy timeout, and transactions that update workflow state and
append its domain event together.

The MVP enforces one non-terminal flow per project in the database, not only in the Skill prompt.

## State Machine

```text
quick flow_start             -> implementing
standard/deep flow_start     -> draft
spec_submit(draft)           -> ready
flow_claim(ready)            -> implementing
gate_run failed              -> implementing
gate_run passed              -> gate_passed
landing_request(gate_passed) -> waiting_owner
```

`flow_start` is an explicit runtime operation, not a transport shortcut. For quick work it creates
and claims the flow atomically so the product's two-call budget is real.

## Tool Inventory

Expose exactly:

| Tool | Mutation | Purpose |
| --- | --- | --- |
| `project_status` | no | Return managed state, the one active flow if present, latest gate state, and one next action. |
| `project_init` | yes | Create the small project-local state boundary after owner confirmation. |
| `flow_start` | yes | Create a quick, standard, or deep flow; quick enters implementation atomically. |
| `spec_submit` | yes | Store one compact standard/deep spec. |
| `flow_claim` | yes | Claim a ready standard/deep flow. |
| `gate_run` | yes | Run configured checks and persist compact evidence. |
| `landing_request` | yes | Move a passed flow to `waiting_owner`. |

No model-callable approval tool exists.

## Input Schemas

All input schemas are closed with `additionalProperties: false`.

Important constraints include:

- `project_root`: non-empty string;
- `flow_id`: non-empty stable identifier;
- `risk`: enum `quick | standard | deep`;
- title, goal, acceptance, and boundaries: trimmed non-empty strings with bounded size;
- expected files: bounded, unique project-relative paths;
- no generic arbitrary metadata object.

Invalid input, invalid transition, unmanaged mutation, active-flow conflict, missing flow, failed
gate, and landing wait are structured domain outcomes. Raw exceptions never cross MCP.

## Response Contract

Success:

```json
{
  "ok": true,
  "data": {},
  "next_action": {
    "tool": "flow_start",
    "reason_code": "project_ready"
  }
}
```

Error:

```json
{
  "ok": false,
  "error": {
    "code": "active_flow_exists",
    "message": "A non-terminal flow already exists.",
    "retryable": true
  },
  "next_action": {
    "tool": "project_status",
    "reason_code": "resume_active_flow"
  }
}
```

`next_action` is optional and singular in both shapes.

MCP results provide the same object as structured content and as serialized JSON text. Correctable
domain failures set the MCP tool-execution error signal while preserving the structured error
object.

The verified FastMCP 3.4.4 environment supports this directly through
`ToolResult(content=..., structured_content=..., is_error=...)`. Use that explicit result type for
the transport boundary; do not raise a text-only exception for a structured domain failure.

## Gate Execution

Gate commands are explicit project configuration. OnlyiFlow does not infer a project's language or
silently install its test tools.

Each command runs without a shell, with tokenized arguments, a bounded timeout, and the resolved
project root as its working directory.

`config.toml` uses version `1` and one to 32 explicit checks:

```toml
version = 1

[[checks]]
id = "tests"
required = true
command = ["python", "-m", "unittest", "discover", "-s", "tests", "-v"]
timeout_seconds = 120
```

Check IDs use lowercase letters, digits, underscores, or hyphens and are unique
case-insensitively. Commands contain one to 32 non-empty argument tokens, and timeouts are between
one and 900 seconds. Invalid or empty configuration fails without guessing a project toolchain.

Persist and return only:

```text
check_id
required
passed
reason_code
duration_ms
exit_code
```

Do not persist or serialize command text, cwd, stdout, or stderr. The host agent may run failing
commands directly when it needs detailed diagnostics.

Project initialization and gate-configuration UX must be evaluated separately from steady-state
quick-flow latency. The implementation plan must not hide one-time setup calls inside the quick
budget.

## Skill Boundary

The Skill:

1. calls `project_status` once;
2. asks before `project_init` when unmanaged;
3. starts or resumes the one active flow;
4. leaves exploration, editing, debugging, and test strategy to the host;
5. invokes `gate_run` only when the user asks to check or land;
6. invokes `landing_request` only after a passed gate;
7. reports one state and one next action, then stops.

It does not create self-tracking TODOs, invoke another methodology Skill, spawn subagents, require a
worktree, or run subjective review loops.

## Host Packaging Boundary

### Codex

Use the documented `.codex-plugin/plugin.json`, Codex-only root `skills/`, and bundled MCP
configuration inside the generated Codex marketplace candidate.
The installed Skill is explicitly invoked as `$onlyiflow:onlyiflow`; the unqualified plugin-local
name is not release evidence.
Local development may use one disposable owner-approved local marketplace entry. The test must
prove that Codex runs the installed cache copy. Current public documentation does not explicitly
promise plugin-root variable substitution in MCP configuration, so the launcher must first prove
plugin-relative `cwd` and arguments and must not embed a versioned cache path.

### Claude Code

Use the generated Claude-only root with `.claude-plugin/plugin.json`, its declared
`skills-claude/`, plugin-owned MCP configuration, and `disable-model-invocation: true`. Explicit
invocation uses the namespaced slash command. Development uses `--plugin-dir`; bundled paths use
the documented `${CLAUDE_PLUGIN_ROOT}` substitution. Do not call `claude mcp add`.
The current explicit command is `/onlyiflow:onlyiflow`.

### ZCode

Treat Desktop folder/marketplace import as authoritative. A locally observed
`.zcode-plugin/plugin.json` candidate may be prepared, but its acceptance is owner-assisted and
must be proven through the ZCode UI. The embedded CLI is a read-only/preflight aid unless the owner
authorizes a lifecycle mutation. Give the owner the generated ZCode-only root, never the source
repository root.

## Testing Boundary

Implementation uses tests first. Required suites include:

- pure transition tests;
- unmanaged read/no-write tests;
- project initialization tests;
- one-active-flow concurrency tests;
- exact seven-tool inventory and deterministic order;
- closed input and output schemas;
- success and error MCP result mapping;
- gate privacy tests;
- copied-plugin and paths-with-spaces stdio tests;
- Skill static prohibitions and prompt non-trigger evaluations;
- Codex and Claude live loader smoke;
- owner-assisted ZCode release smoke.

No unit test uses a real model, user credential, user-level plugin mutation, or network call.

Task 3 automated acceptance covers the transition, initialization, concurrency, schema, copied
stdio, malformed-input, gate, privacy, and landing contracts. Skill prompt evaluations, live
enabled/disabled host behavior, and owner-assisted ZCode import remain later task gates.
