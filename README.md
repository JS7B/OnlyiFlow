# OnlyiFlow

[简体中文](README.zh-CN.md) | English

OnlyiFlow is a project-local development workflow plugin for Codex, Claude Code, and ZCode. It
combines an explicitly invoked Skill, a deterministic local stdio MCP server, and SQLite-backed
workflow state.

The host coding agent owns planning, implementation, debugging, and testing. OnlyiFlow coordinates
explicit flow state, deterministic quality Gates, bounded Wave plans, and landing evidence.

## Capabilities

- Initialize project-local workflow state after owner confirmation.
- Configure deterministic project Gates after a separate owner confirmation.
- Start `quick`, `standard`, or `deep` flows according to change risk.
- Record compact specifications and explicit implementation claims.
- Guide confirmed standard or deep goals through versioned Waves and bounded work packages.
- Run configured quality checks and retain structured Gate evidence.
- Prepare an owner-facing landing request after all required checks pass.
- Close owner-completed flows without deleting their retained history.
- Expose a concise workflow contract as an optional MCP Resource.
- Provide consistent workflow semantics across Codex, Claude Code, and ZCode packages.

## Releases

- `v0.1.0` — Established the explicitly invoked Skill, project-local SQLite state, deterministic
  MCP workflow, `quick`/`standard`/`deep` risk levels, quality Gates, and landing handoff.
- `v0.2.0` — Added persistent Claude Code `user`-scope installation through a retained local
  Marketplace and a user-selected Python environment.
- `v0.3.0` — Added owner-confirmed Gate configuration, project readiness reporting, and a bounded
  migration path for older active flows with an empty Gate.
- `v0.4.0` — Added the optional deep-only Wave workflow, versioned work-package plans, three Wave
  tools, and the bounded `onlyiflow://contract/concise` MCP Resource. This is the current release.

The current source tree is an unreleased `0.5.0` development candidate. It adds optional Wave mode
for `standard` work and the owner-confirmed `flow_close` terminal transition. `v0.4.0` remains the
current GitHub release until separate release authorization and acceptance are complete.

## Requirements

- Python 3.11 or newer
- The packages declared in `requirements.txt`
- Codex, Claude Code, or ZCode
- A local repository checkout when building host packages from source

Select any Python environment and make its `python` command available to the host process. Install
the runtime dependencies into that environment:

```powershell
python --version
python -m pip install -r requirements.txt
```

## Build Host Packages

From the repository root, generate isolated host packages:

```powershell
python -B scripts\build_loader_candidates.py
```

The command creates:

```text
build/loader-candidates/codex-marketplace/
build/loader-candidates/claude-marketplace/
build/loader-candidates/zcode/
```

Use an empty output directory for each fresh build. Every generated host package is
self-contained.

## Install And Start

### Codex

Replace `<codex>` with a working Codex CLI command and `<repository-root>` with the absolute path
to this repository:

```powershell
<codex> plugin marketplace add "<repository-root>\build\loader-candidates\codex-marketplace" --json
<codex> plugin add onlyiflow@onlyiflow-dev --json
```

Start a new Codex task, then invoke:

```text
$onlyiflow:onlyiflow
```

### Claude Code

Copy or extract `build/loader-candidates/claude-marketplace/` to a stable local directory. Replace
`<retained-claude-marketplace>` with that directory:

```powershell
python -m pip install -r "<retained-claude-marketplace>\plugins\onlyiflow\requirements.txt"
claude plugin marketplace add "<retained-claude-marketplace>" --scope user
claude plugin install onlyiflow@onlyiflow-local --scope user
```

Start a fresh Claude Code session in the target project, then invoke:

```text
/onlyiflow:onlyiflow
```

### ZCode

1. Open **Plugin Management** and choose **Add Marketplace**.
2. Select `build/loader-candidates/zcode/`.
3. Install `onlyiflow` from the local Marketplace.
4. Start a new task in the target project and select the OnlyiFlow Skill in the composer.

## Uninstall

Close active host sessions before changing plugin state. Removing the host plugin does not remove
project-local `.onlyiflow/` workflow state.

### Codex

```powershell
<codex> plugin remove onlyiflow@onlyiflow-dev --json
<codex> plugin marketplace remove onlyiflow-dev
```

Start a new Codex task after removal.

### Claude Code

```powershell
claude plugin uninstall onlyiflow@onlyiflow-local --scope user --yes
claude plugin marketplace remove onlyiflow-local --scope user
```

After both commands succeed, the retained local Marketplace directory may be removed. Start a new
Claude Code session to refresh the available Skill and MCP inventory.

### ZCode

1. Open **Plugin Management** and switch to **Installed**.
2. Remove `onlyiflow`.
3. Confirm that its Skill and MCP server are no longer loaded.
4. Remove the local Marketplace source from **Discover** only when it is no longer needed.

## Run A Workflow

Only explicit OnlyiFlow requests activate the workflow. Combine the host-specific invocation with
one concrete instruction.

| Host        | Invocation                                              |
| ----------- | ------------------------------------------------------- |
| Codex       | `$onlyiflow:onlyiflow <instruction>`                  |
| Claude Code | `/onlyiflow:onlyiflow <instruction>`                  |
| ZCode       | Select the OnlyiFlow Skill, then enter`<instruction>` |

### Common Instructions

| Intent             | Example instruction                                                                    |
| ------------------ | -------------------------------------------------------------------------------------- |
| Initialize         | `initialize this project for OnlyiFlow and stop at each owner-confirmation boundary` |
| Quick change       | `start a quick flow for the cache-key bug`                                           |
| Standard change    | `start a standard flow for the authentication change`                                |
| Standard Wave      | `start a standard Wave flow for the authentication change`                           |
| Deep direct change | `start a deep direct flow for the storage migration`                                 |
| Deep Wave change   | `start a deep Wave flow for the storage migration`                                   |
| Resume             | `resume the active OnlyiFlow flow and report one next action`                        |
| Check              | `check the active flow with its configured Gate`                                     |
| Land               | `land the Gate-passed flow and record the owner handoff`                             |
| Close              | `close the externally landed flow and preserve its history`                          |
| Abandon            | `abandon the active flow because its goal was superseded`                            |

For example, a complete Codex Wave invocation is:

```text
$onlyiflow:onlyiflow start a deep Wave flow for this migration goal
```

### First Use In A Project

The first explicit request establishes two owner-confirmed boundaries:

```text
project_status
  -> owner confirms project initialization
project_init
  -> host presents the complete Gate proposal
  -> owner confirms the Gate configuration
gate_configure
  -> project ready
```

`project_status` is read-only. `project_init` creates exactly:

```text
<project>/.onlyiflow/
  onlyiflow.db
  config.toml
  specs/
```

The host presents every Gate check, command, required flag, and timeout before the separate
confirmation that authorizes `gate_configure`.

### Direct Flows

| Risk         | Use                                             | Route to implementation                                       |
| ------------ | ----------------------------------------------- | ------------------------------------------------------------- |
| `quick`    | Small, well-understood changes                  | `project_status -> flow_start`                              |
| `standard` | Changes needing one compact specification       | `project_status -> flow_start -> spec_submit -> flow_claim` |
| `deep`     | High-risk work needing owner-confirmed planning | `project_status -> flow_start -> spec_submit -> flow_claim` |

A configured `quick` flow enters `implementing` atomically. `standard` and direct `deep` flows
start in `draft`, store one compact specification, and enter implementation through `flow_claim`.
Deep planning adds an owner-confirmation boundary before persistence.

### Wave Flows

Wave mode is optional and available for `standard` or `deep` goals. `quick` Wave is invalid.
Request Wave explicitly when the work benefits from a versioned dependency plan and bounded work
packages. Selecting standard Wave does not add deep-risk confirmation ceremony.

The start and confirmation turns are separate:

```text
Start turn:
project_status -> flow_start(mode="wave")
  -> host presents the complete Wave and work-package plan
  -> stop for owner confirmation

Confirmation turn:
project_status -> spec_submit -> wave_plan_set -> flow_claim
  -> state: implementing
```

The complete plan defines the goal, invariants, non-goals, package dependencies, Wave numbers,
allowed and forbidden paths, deliverables, acceptance conditions, authorization requirements, and
conflict reasoning. Plan confirmation does not authorize dependency installation, external writes,
Git operations, or publication unless the owner grants them separately.

The host decides whether and how to use native agents, worktrees, reviews, and Git while executing
the confirmed plan.

During implementation:

1. `project_status` reports the current Wave and one next action.
2. `work_package_status` returns one target package contract.
3. The host performs the implementation, review, testing, worktree, or agent actions it chooses.
4. `work_package_record` records the completed host action.
5. Integrated dependencies unlock packages in later Waves.
6. Material replanning requires another complete `wave_plan_set` revision and owner confirmation.
7. The final Gate remains unavailable until every package is `integrated` or a conditional package
   is validly `deferred`.

`work_package_record` supports these closed actions:

```text
start
submit
request_changes
accept
integrate
interrupt
block
resume
defer
```

These actions record host work; they do not execute an agent, worktree, review, command, or Git
operation.

### Check And Land

An explicit check instruction invokes `gate_run`. Required failures keep the flow in
`implementing`; a passing Gate moves it to `gate_passed`.

An explicit land instruction after a passing Gate invokes `landing_request` and records
`waiting_owner`. Commit, merge, push, and release remain owner-controlled host actions.

After external landing is complete, `flow_close(action="landed",
reason_code="external_landing_completed")` records the separately confirmed terminal decision.
Any non-terminal flow may instead be closed as `abandoned` with one of the supported reason codes.
Closing releases the active-flow slot while preserving the Flow, spec, Gate, Wave, package, and
event history; it performs no Git or release action.

## MCP Surface

The current unreleased `0.5.0` source exposes twelve deterministic MCP tools. The `v0.4.0` release
contains the first eleven; `flow_close` is the candidate addition.

| Tool                    | Responsibility                                                                    |
| ----------------------- | --------------------------------------------------------------------------------- |
| `project_status`      | Read project readiness, the active flow, current Gate state, and one next action. |
| `project_init`        | Create project-local workflow state after owner confirmation.                     |
| `gate_configure`      | Atomically store the complete owner-confirmed Gate configuration.                 |
| `flow_start`          | Start a `quick`, `standard`, or `deep` direct/Wave flow.                    |
| `spec_submit`         | Store one compact specification for a standard or deep flow.                      |
| `wave_plan_set`       | Store a complete initial Wave plan or confirmed plan revision.                    |
| `flow_claim`          | Move a ready standard or deep flow into implementation.                           |
| `work_package_status` | Read one bounded package contract and its current state.                          |
| `work_package_record` | Record one completed host-owned package transition.                               |
| `gate_run`            | Run configured checks and store compact Gate evidence.                            |
| `landing_request`     | Record the owner-controlled landing handoff after a passed Gate.                  |
| `flow_close`          | Record a confirmed terminal decision, release the active slot, and retain history. |

It also exposes one optional static Resource:

```text
onlyiflow://contract/concise
```

The Resource summarizes the workflow contract without carrying project state. Dynamic state always
comes from `project_status`. OnlyiFlow exposes no MCP Prompt templates.

## Repository Layout

- `src/onlyiflow/`: domain, storage, Gate, Wave, and workflow runtime
- `server/stdio.py`: plugin-local stdio server bootstrap
- `packaging/`: host manifests and Skill resources
- `scripts/build_loader_candidates.py`: host-package builder
- `requirements.txt`: runtime dependency contract

## Core Product Rule

> The host agent owns implementation. OnlyiFlow owns explicit workflow state and deterministic
> landing evidence.
