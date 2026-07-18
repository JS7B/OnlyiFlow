# OnlyiFlow Owner Installation And Release Guide

Version: 0.2.0

Status: verified release-candidate guide; tagging and release require owner approval

## Product Boundary

OnlyiFlow is one explicitly invoked Skill plus one deterministic local stdio MCP server. The host
agent owns repository inspection, implementation, debugging, and testing. OnlyiFlow owns only
project-local workflow state and compact Gate/landing evidence.

The source repository is not an installable universal plugin root. Always build and use the three
isolated candidates described below.

## Prerequisites

The owner prepares these prerequisites outside the plugin lifecycle:

- Python 3.11 or newer in an environment selected by the user;
- the packages listed in `requirements.txt` installed in that environment;
- the selected environment's `python` command available to the host process;
- one supported host CLI or Desktop application; and
- a local clone of this repository when building candidates from source.

OnlyiFlow does not prescribe Conda, virtualenv, a system interpreter, or an environment name. If
using Conda, choose and activate the environment before installing dependencies and starting the
host. The host launcher uses whichever `python` command that process can resolve.

For Claude user-scope installation, extract the generated Claude Marketplace archive to a stable
local path. Keep that retained local Marketplace directory while the plugin is installed. The
verified Claude Code 2.1.197 directory-marketplace loader does not load the installed Skill when
that source directory is moved or deleted.

OnlyiFlow does not automatically install or upgrade Python, FastMCP, a host CLI, or any other
dependency. The user prepares the selected Python environment from the included dependency file.

Prepare and verify the selected Python environment before building:

```powershell
python --version
python -m pip install -r requirements.txt
python -c "import fastmcp; print(fastmcp.__version__)"
```

## Build The Host Candidates

From the repository root:

```powershell
python -B scripts\build_loader_candidates.py
```

The builder refuses to overwrite an existing output tree. If `build/loader-candidates/` already
exists, first preserve or remove only that generated directory after confirming its contents; never
point a recursive cleanup at the repository root.

The command produces:

```text
build/loader-candidates/codex-marketplace/
build/loader-candidates/claude-marketplace/
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

## Claude Code User-Scope Installation

Copy or extract `build/loader-candidates/claude-marketplace/` to a stable local directory outside a
temporary folder. Replace `<retained-claude-marketplace>` below with that directory:

```powershell
python -m pip install -r "<retained-claude-marketplace>\plugins\onlyiflow\requirements.txt"
claude plugin marketplace add "<retained-claude-marketplace>" --scope user
claude plugin install onlyiflow@onlyiflow-local --scope user
```

Start a fresh Claude session in any project after changing plugin state. Explicit invocation is:

```text
/onlyiflow:onlyiflow
```

The candidate uses `${CLAUDE_PLUGIN_ROOT}` to launch its bundled server with the `python` command
available to Claude Code. Do not register a separate user-level MCP server. Retain the extracted
Marketplace directory and keep the selected Python environment available for as long as the plugin
is installed.

Disable, enable, update, or remove only the exact OnlyiFlow entry:

```powershell
claude plugin disable onlyiflow@onlyiflow-local --scope user
claude plugin enable onlyiflow@onlyiflow-local --scope user
claude plugin marketplace update onlyiflow-local
claude plugin update onlyiflow@onlyiflow-local --scope user
claude plugin uninstall onlyiflow@onlyiflow-local --scope user --yes
claude plugin marketplace remove onlyiflow-local --scope user
```

Delete the retained Marketplace directory only after uninstalling the plugin and removing its
Marketplace entry. A fresh `claude plugin list` and `claude plugin marketplace list` must then show
no OnlyiFlow entry; no OnlyiFlow cache or MCP process may remain. Do not modify another Claude
plugin or Marketplace.

## ZCode Owner-Assisted Lifecycle

ZCode Desktop UI is the authoritative lifecycle surface. The embedded CLI is read-only evidence
unless the owner separately authorizes mutation.

1. Open Plugin Management and choose Add Marketplace.
2. Select the directory `build/loader-candidates/zcode/`.
3. Confirm its root `marketplace.json` exposes only `onlyiflow` 0.2.0.
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
python -B -m ruff format --check .
python -B -m ruff check .
python -B -m unittest discover -s tests -v
python -B "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" build\loader-candidates\codex-marketplace\plugins\onlyiflow\skills\onlyiflow
claude plugin validate build\loader-candidates\claude-marketplace
claude plugin validate build\loader-candidates\claude-marketplace\plugins\onlyiflow
python -B scripts\build_loader_candidates.py --output-root "<fresh-empty-output-root>"
```

Run the Claude user-scope lifecycle and model-backed acceptance sequentially. A network or model
timeout is infrastructure evidence, not a product failure; stop after the first infrastructure
failure instead of retrying blindly.

```powershell
python -B scripts\run_claude_user_install_lifecycle.py --timeout-seconds 600
python -B scripts\run_claude_user_install_acceptance.py --timeout-seconds 600
```

The automated reports do not replace the owner-assisted ZCode lifecycle and behavioral smoke.
Release evidence must also prove cleanup: no test plugin, Codex marketplace, plugin cache,
temporary workspace, controller directory, measurement process, or MCP process may remain. The
owner-accepted uninstalled ZCode discovery source is the only documented exception.

## Evidence And Approval

Authoritative evidence is recorded in:

- activation evaluation: `docs/evaluations/2026-07-16-task4-skill-evaluation.md`;
- efficiency and Gate value: `docs/evaluations/2026-07-17-task5-efficiency-and-gate-value.md`;
- three-host release smoke: `docs/evaluations/2026-07-17-task6-three-host-release-smoke.md`;
- release readiness: `docs/evaluations/2026-07-17-task7-release-readiness.md`; and
- Claude user-scope installation: `docs/evaluations/2026-07-18-v0.2.0-claude-user-install.md`.

Tag creation, GitHub Release creation, publication, and any public marketplace release require
separate owner approval. Passing automated checks alone is not that approval.
