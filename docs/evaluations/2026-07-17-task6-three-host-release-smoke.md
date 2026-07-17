# Task 6 Three-Host Release Smoke Evidence

Date: 2026-07-17

Status: Complete. Claude, Codex, and the owner-assisted ZCode Desktop smoke are accepted, and all
temporary workspaces and runtime processes are absent.

## Acceptance Contract

The automated hosts run in disposable Git projects whose paths contain spaces. Each accepted run
must prove:

1. the host loads the generated plugin candidate;
2. an ordinary prompt produces no OnlyiFlow activity;
3. explicit invocation observes the unmanaged project without initializing it;
4. a new owner-confirmation turn initializes the unchanged project;
5. a quick flow reaches `implementing` without a spec;
6. ordinary host implementation performs the code edit with no OnlyiFlow tool call;
7. a configured Gate fails on a real regression, then passes after repair;
8. landing records `waiting_owner`;
9. unloading removes the Skill and tools; and
10. lifecycle cleanup completes with no error or retained test workspace.

The exact accepted tool sequences are shared by Claude and Codex:

| Turn | MCP tools |
| --- | --- |
| ordinary | none |
| initialization request | `project_status` |
| initialization confirmation | `project_status`, `project_init` |
| quick start | `project_status`, `flow_start` |
| implementation | none |
| failing Gate | `project_status`, `gate_run` |
| repair | none |
| passing Gate | `project_status`, `gate_run` |
| landing | `project_status`, `landing_request` |
| post-unload probe | none |

## Test-First Runner

Task 6 added `tests/test_task6_release_smoke.py` before the runner existed. The focused test first
failed because `scripts/run_release_smoke.py` was absent. After the smallest runner implementation,
all three focused report/fixture contract tests passed. The complete local suite then passed 62/62.

The runner writes privacy-safe reports under `build/task6-release-smoke-results/`, classifies model
or network unavailability as infrastructure rather than product failure, and performs the temporary
Codex lifecycle cleanup in `finally`.

## Accepted Automated Evidence

| Host | Accepted report | SHA-256 | Result |
| --- | --- | --- | --- |
| Claude | `build/task6-release-smoke-results/claude-20260717T062655Z.json` | `54A5777F730BFBF43E8E4EF69F674D824CE3EFA2246950E1A73E43EC1B5DA749` | `passed`; 11/11 checks; `cleanup_errors = []` |
| Codex | `build/task6-release-smoke-results/codex-20260717T071941Z.json` | `2EB92327C847FECD43D70D6CD9AE2846C366CB32C93631DF765E196E44E5EC77` | `passed`; 11/11 checks; `cleanup_errors = []` |

Both reports contain the exact sequence above. Independent post-run checks found no OnlyiFlow
Codex plugin, development marketplace, cache directory, Task 6 workspace, or retained measurement
process. Claude's temporary candidate surface was likewise absent after its run.

## Codex Infrastructure Interruption

The first Codex run produced
`build/task6-release-smoke-results/codex-20260717T065154Z.json` with
`error = host_model_or_network_unavailable`. It had already passed ordinary isolation,
owner-confirmed initialization, quick start, host-owned implementation, and the failing-Gate turn.
It failed before the post-repair Gate call and still completed lifecycle cleanup with
`cleanup_errors = []`.

No blind retry was performed. An isolated fixed-marker Codex probe then returned the exact marker
in 4.723 seconds with exit code zero and no tool events. That evidence justified one controlled
full rerun, which became the accepted Codex report above.

## ZCode Owner-Assisted Gate

Read-only discovery on the current host found ZCode Desktop 3.3.1 and embedded CLI 0.15.0. The
read-only `plugins list`, `skills list`, and `doctor` surfaces returned no diagnostics and showed no
OnlyiFlow installation before the gate. The generated owner-imported marketplace root is:

`build/loader-candidates/zcode/`

Its `marketplace.json` points only to the self-contained `onlyiflow/` plugin beneath it. That
plugin's `.zcode-plugin/plugin.json` uses the same current component fields and
plugin-root/project-dir variables observed in a bundled ZCode 3.3.1 plugin. This is structural
evidence only; it does not replace the required Desktop import.

### ZCode 3.3.1 Marketplace Packaging Failure And Repair

The first owner UI attempt correctly rejected the single plugin directory with `Marketplace
manifest not found in directory`. Read-only inspection of the installed ZCode implementation
confirmed that its Add Marketplace directory surface accepts a root `marketplace.json` or
`.claude-plugin/marketplace.json`; it does not treat `.zcode-plugin/plugin.json` as a marketplace
manifest.

A focused foundation contract assertion was added first and failed because
`zcode/marketplace.json` did not exist. The candidate builder now emits the smallest local
marketplace manifest with one `onlyiflow` entry whose source is `./onlyiflow`. The targeted test
then passed. A staged reproducibility comparison proved the prior 40 generated files were
byte-identical and the only new file was `zcode/marketplace.json`; the active candidate now has 41
files. The complete suite passed 62/62, the Codex Skill validator passed, and the Claude plugin
validator passed after this repair.

### Accepted ZCode Owner-Assisted Evidence

The owner added the repaired local marketplace, installed `onlyiflow` 0.1.0, and ran the shared
scenario in a disposable Git project whose path contained spaces. Read-only inspection confirmed
one OnlyiFlow Skill and the declared/active OnlyiFlow MCP server before the smoke. The observed
behavior then passed the release contract:

1. an ordinary prompt explained the source without invoking OnlyiFlow or changing workflow state;
2. the first explicit request reported the unmanaged project and stopped before initialization;
3. a separate owner-confirmation turn initialized the unchanged project and stopped before flow
   creation;
4. the quick flow reached `implementing` with zero specs;
5. ordinary ZCode implementation changed only `app.py`, left the regression test byte-identical,
   and made no Gate call;
6. the first required `regression` Gate failed with exit code 1 and kept the flow in
   `implementing`;
7. after the ordinary repair, the second Gate passed with exit code 0 and moved the flow to
   `gate_passed`;
8. landing moved the flow to `waiting_owner`; and
9. owner removal made the plugin, Skill, and MCP exposure disappear.

The final database contained one quick flow in `waiting_owner`, two Gate records (one failed and
one passed), and zero specs. The test SHA-256 remained
`ED5EA167DE01777C6C9192467C90D2C24718CAB2327BB15541BB519B7B5631E8`.

ZCode 3.3.1 retained the owner-added `onlyiflow-dev` local marketplace after plugin uninstall, so
the Discover page still shows an uninstalled card with the `获取` action. Read-only UI inspection
found no visible marketplace-removal action. This retained source is not counted as loaded plugin
state: `installed_plugins.json` has no plugins, the OnlyiFlow Skill and MCP exposure are absent,
and the versioned plugin cache is empty. The owner explicitly accepted retaining this discoverable
local source.

ZCode did not terminate six already-started OnlyiFlow MCP Python processes when the plugin was
removed. Their command lines all pointed to the removed versioned OnlyiFlow cache entry. Cleanup
terminated only those six exact processes; the post-cleanup OnlyiFlow runtime and measurement
process counts are zero. No unrelated plugin or ZCode process was changed.

Automation only inspected UI/CLI-visible state and the disposable project. The owner performed the
ZCode marketplace addition, plugin installation, and plugin removal actions.

## Final Verification

After the ZCode packaging repair and owner-assisted smoke:

- the complete local suite passed 62/62;
- the Codex Skill validator passed;
- the Claude plugin validator passed;
- two clean candidate rebuilds and the active candidate each contained 41 files with zero hash
  difference and zero bytecode artifacts;
- Codex OnlyiFlow plugin artifacts, Claude OnlyiFlow plugin artifacts, ZCode installed plugin
  records, ZCode versioned cache files, OnlyiFlow runtime processes, and Task measurement processes
  were all zero; and
- one empty legacy Claude `onlyiflow-inline` data directory was removed without touching another
  plugin; and
- after ZCode closed and released its file lock, the disposable owner-smoke workspace was removed
  and the Task 6 temporary-directory count returned to zero.

The owner-retained ZCode local marketplace is the only intentional user-level discovery record. It
does not expose an installed Skill or MCP server.

## Current Completion State

Task 6 is complete. All three hosts passed the release smoke, final repository verification passed,
and lifecycle cleanup is complete. The owner-retained ZCode marketplace is an intentionally
discoverable uninstalled source, not loaded plugin state. Task 7 is now in progress under owner
authorization.
