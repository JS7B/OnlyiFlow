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
- Run configured quality checks and retain structured Gate evidence.
- Prepare an owner-facing landing request after all required checks pass.
- Provide the same workflow semantics across Codex, Claude Code, and ZCode host packages.

## Release Status

The current GitHub release is `v0.3.0`. It includes persistent Claude Code `user`-scope
installation, owner-confirmed Gate configuration, project readiness status, and a bounded upgrade
path for older active flows whose Gate is still empty.

The 0.3.0 release has passed local verification, Claude installed-plugin and release-smoke
acceptance, and the owner-assisted ZCode lifecycle. The retained local Codex installation resolves
to 0.3.0 and remains enabled; live Codex 0.3.0 model verification is deferred by the owner.

The established Claude and Codex release baselines have passed the complete activation,
efficiency/Gate, and release-smoke contracts. The owner-assisted ZCode 0.3.0 lifecycle has passed ordinary-request isolation,
owner-confirmed initialization, quick-flow execution, failing and passing Gates, landing, and
unload verification.

The complete acceptance record is available in
[the v0.3.0 Gate configuration evidence](docs/evaluations/2026-07-19-v0.3.0-gate-configuration.md),
[the v0.2.0 Claude installation evidence](docs/evaluations/2026-07-18-v0.2.0-claude-user-install.md),
and [the v0.1.0 release-readiness audit](docs/evaluations/2026-07-17-task7-release-readiness.md).

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

The complete install, update, removal, and verification procedures are in the
[release guide](docs/release-guide.md).

## Run A Workflow

Invoke OnlyiFlow together with the intended action. For example:

```text
$onlyiflow:onlyiflow start a quick flow for the cache-key bug
/onlyiflow:onlyiflow start a standard flow for the authentication change
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

The Skill coordinates these eight deterministic MCP tools:

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

Every tool resolves an explicit project root and returns a stable structured result with at most
one next action.

## Repository Layers

Product contracts:

- `docs/product-spec.md`: behavior, flow semantics, and product scope
- `docs/engineering-spec.md`: runtime, persistence, transport, packaging, and testing contracts
- `docs/release-guide.md`: installation, lifecycle, verification, and release procedure

Implementation:

- `src/onlyiflow/`: domain, storage, Gate, and workflow runtime
- `server/stdio.py`: plugin-local stdio server bootstrap
- `packaging/`: host manifests and Skill resources
- `scripts/build_loader_candidates.py`: host-package builder

Verification and evidence:

- `tests/`: unit, contract, packaging, and runner tests
- `scripts/run_skill_evaluations.py`, `scripts/run_efficiency_measurements.py`, and
  `scripts/run_release_smoke.py`: release-evidence runners
- `docs/research/`, `docs/plans/`, and `docs/evaluations/`: research, execution plans, and accepted
  evidence

## Core Product Rule

> The host agent owns implementation. OnlyiFlow owns explicit workflow state and deterministic
> landing evidence.
