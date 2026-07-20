# OnlyiFlow

[简体中文](README.zh-CN.md) | English

OnlyiFlow is a project-local development workflow plugin for Codex, Claude Code, and ZCode. It
provides an explicitly invoked Skill, a deterministic local stdio MCP server, and SQLite-backed
workflow state.

The host coding agent performs planning, implementation, debugging, and testing. OnlyiFlow
coordinates flow state, deterministic quality Gates, and landing evidence.

## Capabilities

- Initialize project-local workflow state after owner confirmation.
- Configure deterministic project Gates after a separate owner confirmation.
- Start `quick`, `standard`, or `deep` flows according to the change risk.
- Record compact specifications and explicit implementation claims.
- Guide an explicitly confirmed deep goal through versioned Waves and bounded work packages.
- Run configured quality checks and retain structured Gate evidence.
- Prepare an owner-facing landing request after all required checks pass.
- Offer a concise workflow contract as an optional MCP Resource without adding default context.
- Provide the same workflow semantics across Codex, Claude Code, and ZCode host packages.

## Release Status

The current GitHub release is `v0.3.0`. It includes persistent Claude Code `user`-scope
installation, owner-confirmed Gate configuration, project readiness status, and a bounded upgrade
path for older active flows whose Gate is still empty.

The current source tree is an unpublished `v0.4.0` release candidate. It adds one bounded,
on-demand MCP workflow-contract Resource plus an optional Wave mode for explicitly confirmed deep
goals. Wave mode adds three deterministic tools for plan revisions and package evidence, while
leaving the existing direct quick/standard path unchanged. It adds no MCP Prompt template.

The 0.3.0 release has passed local verification, Claude installed-plugin and release-smoke
acceptance, and the owner-assisted ZCode lifecycle. The retained local Codex installation resolves
to 0.3.0 and remains enabled; live Codex 0.3.0 model verification is deferred by the owner.

The established Claude and Codex release baselines have passed the complete activation,
efficiency/Gate, and release-smoke contracts. The owner-assisted ZCode 0.3.0 lifecycle has passed
ordinary-request isolation, owner-confirmed initialization, quick-flow execution, failing and
passing Gates, landing, and unload verification. The owner-assisted ZCode 3.3.6 Wave acceptance
for the `v0.4.0` candidate has also passed its proposal, confirmation/claim, resume, unload, and
cleanup scenarios. Live Claude and Codex Wave acceptance remains pending.

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

Use an empty output directory for each fresh build. The generated directory for each host is
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

1. Open **Plugin Management** and select **Add Marketplace**.
2. Select `build/loader-candidates/zcode/`.
3. Install `onlyiflow` from the local Marketplace.
4. Start a new task in the target project and explicitly invoke the OnlyiFlow Skill.

## Update An Existing Installation

Download or check out the intended newer release, build it into a fresh empty output root, and
validate the generated packages before replacing any retained Marketplace directory:

```powershell
python -B scripts\build_loader_candidates.py --output-root "<fresh-output-root>"
```

Close the host being updated. Replace only that host's retained Marketplace directory with the
corresponding validated directory from `<fresh-output-root>`, then use its native update path.

### Update Codex

Keep the existing `onlyiflow-dev` Marketplace registration and refresh the installed cache from
the newly built Marketplace:

```powershell
<codex> plugin add onlyiflow@onlyiflow-dev --json
```

A version change such as `0.4.0` to a later release is reflected by the rebuilt manifest. Start a new Codex
task after the command succeeds.

### Update Claude Code

Keep the retained `onlyiflow-local` directory and its user-scope Marketplace registration. After
replacing that directory with the new build, run:

```powershell
claude plugin marketplace update onlyiflow-local
claude plugin update onlyiflow@onlyiflow-local --scope user
```

Start a fresh Claude Code session after both commands succeed.

### Update ZCode

Use ZCode Desktop as the installation surface:

1. Remove the installed OnlyiFlow plugin from **Installed**.
2. Replace or refresh the retained local Marketplace with the new `zcode/` build.
3. Install OnlyiFlow again from **Discover**.
4. Start a new task and confirm the Skill and MCP server are visible.

Updating the host package does not recreate project-local `.onlyiflow/` state. Synchronize the
selected Python environment with the new `requirements.txt` when its dependency list changes, and
leave unrelated plugins and Marketplaces unchanged.

The commands above cover the supported install, update, and removal paths for each host.

## Run A Workflow

Invoke OnlyiFlow together with the intended action. For example:

```text
$onlyiflow:onlyiflow start a quick flow for the cache-key bug
/onlyiflow:onlyiflow start a standard flow for the authentication change
$onlyiflow:onlyiflow start a deep Wave flow for this migration goal
```

On first use in a project:

1. OnlyiFlow reports the project status.
2. The host presents the project-local state entries for owner confirmation.
3. After confirmation, OnlyiFlow initializes the project.
4. The host proposes the Gate checks and waits for a separate owner confirmation.
5. OnlyiFlow stores the confirmed Gate configuration, then starts the requested flow.
6. The host agent implements and tests the change while OnlyiFlow records the flow state.
7. An explicit `check` request runs the configured Gate.
8. An explicit `land` request records the landing handoff after the Gate passes.

`quick` flows enter implementation directly. `standard` flows use one compact specification.
`deep` flows add an owner-confirmation turn before detailed planning.

For a deep goal that explicitly requests Wave mode, the host presents one complete package plan
and waits for a separate confirmation. OnlyiFlow then records the versioned plan and exposes only
the package needed for the current Wave. The host decides whether and how to use native agents,
worktrees, reviews, and Git; after those host actions occur, OnlyiFlow records compact package
handoffs and integration evidence. Dependencies unlock only after their packages are recorded as
integrated, and the final project Gate remains unavailable until every package is integrated or a
conditional package is explicitly deferred. Material replanning requires another complete plan
and owner confirmation.

If an upgraded project already has an active flow but its Gate is still empty, OnlyiFlow uses the
same proposal and separate owner-confirmation boundary for the first Gate, then resumes that flow.
Configured Gates remain locked while a flow is active.

## State And Tool Model

Managed projects store state under:

```text
<project>/.onlyiflow/
  onlyiflow.db
  config.toml
  specs/
```

The current development Skill coordinates these eleven deterministic MCP tools:

```text
project_status
project_init
gate_configure
flow_start
spec_submit
wave_plan_set
flow_claim
work_package_status
work_package_record
gate_run
landing_request
```

Every tool resolves an explicit project root and returns a stable structured result with at most
one next action.

## Repository Layout

- `src/onlyiflow/`: domain, storage, Gate, and workflow runtime
- `server/stdio.py`: plugin-local stdio server bootstrap
- `packaging/`: host manifests and Skill resources
- `scripts/build_loader_candidates.py`: host-package builder
- `requirements.txt`: runtime dependency contract

## Core Product Rule

> The host agent owns implementation. OnlyiFlow owns explicit workflow state and deterministic
> landing evidence.
