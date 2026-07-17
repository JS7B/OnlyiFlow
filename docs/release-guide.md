# OnlyiFlow Owner Installation And Release Guide

Version: 0.1.0

Status: verified release-candidate guide; commit, push, and release require owner approval

## Product Boundary

OnlyiFlow is one explicitly invoked Skill plus one deterministic local stdio MCP server. The host
agent owns repository inspection, implementation, debugging, and testing. OnlyiFlow owns only
project-local workflow state and compact Gate/landing evidence.

The source repository is not an installable universal plugin root. Always build and use the three
isolated candidates described below.

## Prerequisites

The owner prepares these prerequisites outside the plugin lifecycle:

- Python 3.11 or newer in the Conda environment named `myself`;
- `fastmcp>=3.4,<4` available in that environment;
- `conda` available to the host process;
- one supported host CLI or Desktop application; and
- a local clone of this repository.

OnlyiFlow does not install or upgrade Python, FastMCP, a host CLI, or any other dependency. The
Skill, MCP server, manifests, and host lifecycle contain no dependency-install command.

Verify the approved Python environment before building:

```powershell
conda run --no-capture-output -n myself python -s -B -c "import sys, fastmcp; print(sys.version.split()[0]); print(fastmcp.__version__)"
```

## Build The Host Candidates

From the repository root:

```powershell
conda run --no-capture-output -n myself python -s -B scripts\build_loader_candidates.py
```

The builder refuses to overwrite an existing output tree. If `build/loader-candidates/` already
exists, first preserve or remove only that generated directory after confirming its contents; never
point a recursive cleanup at the repository root.

The command produces:

```text
build/loader-candidates/codex-marketplace/
build/loader-candidates/claude/onlyiflow/
build/loader-candidates/zcode/
```

Do not import the repository root, the Claude candidate into Codex, or the single
`build/loader-candidates/zcode/onlyiflow/` directory into ZCode.

## Codex Installation And Removal

Use a Codex CLI executable whose `--version` command succeeds. Use one launcher consistently within
a release-evidence set; observed launcher versions belong in the evaluation evidence.

Replace `<working-codex-cli>` below with the working command or native executable path, and replace
`<repository-root>` with the absolute repository path:

```powershell
<working-codex-cli> plugin marketplace add "<repository-root>\build\loader-candidates\codex-marketplace" --json
<working-codex-cli> plugin add onlyiflow@onlyiflow-dev --json
```

Start a new Codex task after changing plugin state. Explicit invocation is:

```text
$onlyiflow:onlyiflow
```

Remove the plugin and temporary test marketplace after testing or when uninstalling:

```powershell
<working-codex-cli> plugin remove onlyiflow@onlyiflow-dev --json
<working-codex-cli> plugin marketplace remove onlyiflow-dev
```

Confirm `plugin list --json` and `plugin marketplace list` contain no OnlyiFlow entry, and confirm
the OnlyiFlow cache and MCP process are absent. Do not modify unrelated Codex plugins.

## Claude Code Session Loading

Claude Code needs no persistent installation for the verified owner path. From the project to be
worked on, start a fresh session with the generated candidate:

```powershell
claude --plugin-dir "<repository-root>\build\loader-candidates\claude\onlyiflow"
```

Explicit invocation is:

```text
/onlyiflow:onlyiflow
```

The candidate uses `${CLAUDE_PLUGIN_ROOT}` to launch its bundled server. Do not register a separate
user-level MCP server. Ending the session unloads the candidate; `claude plugin list` should still
contain no installed OnlyiFlow plugin.

## ZCode Owner-Assisted Lifecycle

ZCode Desktop UI is the authoritative lifecycle surface. The embedded CLI is read-only evidence
unless the owner separately authorizes mutation.

1. Open Plugin Management and choose Add Marketplace.
2. Select the directory `build/loader-candidates/zcode/`.
3. Confirm its root `marketplace.json` exposes only `onlyiflow` 0.1.0.
4. Select `获取`/install on the OnlyiFlow card.
5. Confirm one OnlyiFlow Skill and the OnlyiFlow MCP server are visible.
6. Invoke OnlyiFlow explicitly and run the required owner-confirmed workflow.
7. Remove the plugin through the Installed view.
8. Confirm the Skill and MCP exposure disappear, then close ZCode before final filesystem cleanup.

If ZCode retains the owner-added local marketplace as an uninstalled Discover source, the retained
card is acceptable only when it shows the install action and there is no installed plugin, Skill,
MCP exposure, versioned cache, temporary project, or OnlyiFlow runtime process. Do not change
another ZCode plugin or marketplace.

## First Use In A Project

Ordinary coding prompts must not invoke OnlyiFlow. On the first explicit request:

1. `project_status` reports that the project is unmanaged and creates nothing.
2. The host explains the exact `.onlyiflow/` entries and waits.
3. Only after owner confirmation may `project_init` create local state.
4. A managed quick flow reaches `implementing` through `project_status` then `flow_start` and creates
   no spec.

OnlyiFlow state is project-local:

```text
<project>/.onlyiflow/
  onlyiflow.db
  config.toml
  specs/
```

## Enforcement Boundary

OnlyiFlow records a deterministic Gate result and a request to land. It does not intercept or
prevent `git push`, `git merge`, direct commits, or another landing mechanism. The Skill and MCP
server are guidance and evidence surfaces, not repository enforcement.

Enforce mandatory repository checks externally with CI and branch protection. An owner-managed Git
hook may add local protection, but it is outside this first plugin increment and is never installed
by OnlyiFlow.

Human approval remains outside model-callable tools. `landing_request` records `waiting_owner`; it
does not grant owner approval or perform the landing operation.

## Complete Release Verification

Run formatting, linting, local tests, candidate validation, and a fresh non-overwriting candidate
build before any model-backed verification. Replace `<fresh-empty-output-root>` with a path that
does not yet exist, then compare that build with the active candidates:

```powershell
conda run --no-capture-output -n myself python -s -B -m ruff format --check .
conda run --no-capture-output -n myself python -s -B -m ruff check .
conda run --no-capture-output -n myself python -s -B -m unittest discover -s tests -v
conda run --no-capture-output -n myself python -s -B "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" build\loader-candidates\codex-marketplace\plugins\onlyiflow\skills\onlyiflow
claude plugin validate build\loader-candidates\claude\onlyiflow
conda run --no-capture-output -n myself python -s -B scripts\build_loader_candidates.py --output-root "<fresh-empty-output-root>"
```

Run model-backed hosts sequentially. A network or model timeout is infrastructure evidence, not a
product failure; stop after the first infrastructure failure instead of retrying blindly.

```powershell
conda run --no-capture-output -n myself python -s -B scripts\run_skill_evaluations.py --host claude --mode both --timeout-seconds 600
conda run --no-capture-output -n myself python -s -B scripts\run_skill_evaluations.py --host codex --mode both --timeout-seconds 600 --allow-codex-plugin-lifecycle
conda run --no-capture-output -n myself python -s -B scripts\run_efficiency_measurements.py --host claude --timeout-seconds 600
conda run --no-capture-output -n myself python -s -B scripts\run_efficiency_measurements.py --host codex --timeout-seconds 600 --allow-codex-plugin-lifecycle
conda run --no-capture-output -n myself python -s -B scripts\run_release_smoke.py --host claude --timeout-seconds 600
conda run --no-capture-output -n myself python -s -B scripts\run_release_smoke.py --host codex --timeout-seconds 600 --allow-codex-plugin-lifecycle
```

The automated reports do not replace the owner-assisted ZCode lifecycle and behavioral smoke.
Release evidence must also prove cleanup: no test plugin, Codex marketplace, plugin cache,
temporary workspace, controller directory, measurement process, or MCP process may remain. The
owner-accepted uninstalled ZCode discovery source is the only documented exception.

## Evidence And Approval

Authoritative evidence is recorded in:

- activation evaluation: `docs/evaluations/2026-07-16-task4-skill-evaluation.md`;
- efficiency and Gate value: `docs/evaluations/2026-07-17-task5-efficiency-and-gate-value.md`;
- three-host release smoke: `docs/evaluations/2026-07-17-task6-three-host-release-smoke.md`; and
- release readiness: `docs/evaluations/2026-07-17-task7-release-readiness.md`.

Commit, push, publication, and any public marketplace release require separate owner approval.
Passing automated checks alone is not that approval.
