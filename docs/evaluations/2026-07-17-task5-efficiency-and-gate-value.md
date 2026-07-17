# Task 5 Efficiency And Gate Value

Date: 2026-07-17

Status: Complete from accepted recovery-host evidence; strict-isolation follow-up handed off for
optional recovery-host remeasurement

## Scope

Task 5 measures rather than expands the product. For each verified host, the runner records only:

- wall-clock time;
- model turns;
- MCP calls before the first code edit;
- total MCP calls;
- Gate failures caught before landing;
- task success and regression result.

The paired disabled/enabled baseline, first-use initialization, managed quick flow, and managed
standard flow are separate measurements. The quick and standard flows each include an intentional
fault injection after a successful implementation, a failed deterministic Gate, an ordinary
host-owned repair turn, a passing Gate, and an owner-controlled landing request.

Reports contain aggregate metrics and acceptance booleans only. They do not persist prompts,
assistant replies, commands, cwd, stdout, stderr, transcripts, credentials, project paths, or raw
Gate output.

## Implemented Checkpoint

- `scripts/run_efficiency_measurements.py` reuses the proven Task 4 host commands, exact MCP event
  parsing, and temporary Codex lifecycle.
- `tests/test_task5_measurements.py` covers metric aggregation, the ceremony budgets, report
  privacy, source-edit detection, Claude argument boundaries, and the deterministic failing-then-
  passing Gate fixture.
- The runner keeps implementation turns ordinary and requires zero OnlyiFlow calls during them.
- Claude measurements disable prompt suggestions and use `--strict-mcp-config`. Disabled mode gets
  an empty MCP map; enabled mode gets one explicit OnlyiFlow server rendered from the tracked
  Claude MCP template. Other user, project, and plugin MCP configurations cannot enter the
  measurement.
- `--preflight-only` checks the generated candidate, the `myself` Python/FastMCP runtime, the
  selected host CLI, and either Claude candidate validation or a clean Codex test lifecycle. It
  performs no model call and makes no plugin change.
- Managed quick must start with exactly `project_status -> flow_start` and no spec or plan.
- Managed standard must start with exactly `project_status -> flow_start -> spec_submit ->
  flow_claim` and exactly one compact spec.
- The Windows temporary-directory cleanup uses a verified system-temp root plus bounded retries.
  This avoids Python's recursive cleanup failure when a host child briefly retains its cwd.
- Before integration, the recovery-host branch passed 59 tests and the strict-isolation branch
  passed 62 tests. The merged suite now passes all 63 tests, including 11 focused Task 5 tests.

## Interrupted Live Evidence

At that interrupted checkpoint, no Task 5 report had been accepted.

Claude:

- the paired baseline and separate two-turn initialization completed in the first full attempt;
- quick reached its second Gate but the database did not enter `gate_passed` even though the
  runner's direct regression command passed immediately before the Gate;
- the runner now includes only compact latest-Gate metadata in that failure message so a recurrence
  will distinguish `check_failed`, `check_timeout`, or `check_launch_error` without raw output;
- the direct fixture test proves the same configured Gate fails on the injected bug and passes
  after the repair;
- two later quick-only retries ended at the first model call with infrastructure errors after about
  183 seconds;
- the original fixed-marker probe also exceeded its outer timeout, but it did not isolate MCP or
  Skill discovery, so that result is no longer sufficient evidence of a network failure;
- a strict probe from the system temporary directory, with an empty MCP map and slash commands
  disabled, returned `ONLYIFLOW_NETWORK_OK` in 7.58 seconds with exit code zero;
- that result reported one main `glm-5.2[1M]` turn through the configured third-party Anthropic-
  compatible provider plus a small `glm-4.5-air` auxiliary use. The runner now passes
  `--prompt-suggestions false` to remove that irrelevant auxiliary request;
- the repaired strict-isolation runner has not yet been used for an accepted live report.

Codex:

- a plugin-free fixed-marker probe succeeded after WebSocket retries and HTTPS fallback in about
  121 seconds;
- the full measurement completed disabled and enabled baselines plus the separate initialization;
- quick completed its exact two-call start and was in the ordinary implementation turn when the
  owner requested a stop;
- the interrupted run produced no accepted report.

After stopping, all Task 5 runners and child processes were terminated. The temporary Codex plugin,
marketplace, cache directory, and all Task 5 temporary workspaces were removed and verified absent.

## New-Machine Recovery And Probe Evidence

A fresh clone was restored with clean `main` and `origin/main` both at
`6107ba850821283bc216f1d2a1342b03ec308c9a`. Generated loader candidates and the two accepted Task 4
reports were restored from the old-machine handoff.

- The `myself` environment initially lacked the declared FastMCP dependency. After owner approval,
  FastMCP 3.4.4 was installed because that is the version family verified by the engineering
  evidence. Pip also reported conflicts between its required transitive versions and unrelated
  FastAPI, Gradio, and Semantic Kernel packages already present in the shared environment; no
  unrelated dependency was adjusted. The OnlyiFlow suite passes with the installed runtime.
- The new host uses a WinGet-native Claude CLI and a Codex Desktop-native CLI. The old npm-only
  resolver could not launch Claude and selected an incomplete npm Codex package. The resolver now
  validates native Windows executables first and retains the proven npm entry points as fallbacks.
- Before live fixes, all 58 local tests passed. The Codex Skill validator, Claude plugin validator,
  and `git diff --check` also passed.
- The first new-machine probe used Claude's bare mode, which does not load the normal settings that
  supply this host's GLM Coding Plan endpoint and token. Its 192.793-second result is therefore not
  accepted as network evidence. A corrected provider-aware probe then loaded the normal GLM
  settings while exposing an empty tool list, an empty strict MCP configuration, and no Skills. It
  returned code 1 after 186.082 seconds without the fixed marker. This is treated as GLM
  provider/model unavailability rather than a product failure, consistent with the earlier
  approximately 183-second infrastructure failures.
- After the owner selected `glm-5.2`, the same provider-aware Claude probe returned the exact
  `ONLYIFLOW_NETWORK_OK` marker with exit code 0 and `is_error=false` in 20.574 seconds. The API
  duration was 16.434 seconds with no retry amplification, so live measurement resumed.
- A Codex probe used `gpt-5.6-sol` with priority service, isolated user configuration, plugins and
  optional tool features disabled, and a system-temporary working directory. It returned the exact
  `ONLYIFLOW_CODEX_NETWORK_OK` marker with exit code 0 in 6.268 seconds and emitted no tool event.

## Product Failures And Test-First Fixes

The first resumed Claude run reached the repaired quick flow but its second Gate recorded
`check_timeout` after 60 seconds. The runner's direct regression invocation closed stdin while the
real Gate process inherited the Claude MCP stdio input pipe. A new Gate contract assertion first
failed because `stdin` was absent; `run_gate_check` now passes `stdin=subprocess.DEVNULL`. The Gate
and focused Task 5 suites passed, generated candidates were rebuilt, and the next Claude run passed.

The first Codex run after that fix had a one-run `quick_passed_gate_unexpected_mcp_sequence` model
deviation. The runner now reports only the expected and actual tool-name arrays on such failures;
the new privacy-safe diagnostic test failed first and then passed. The deviation did not recur.

The next Codex run reached `standard_start` but edited a source file during the explicit workflow
start turn. The Skill described the required tool sequence but did not state a separate stop
boundary after entering `implementing`. A Skill contract test first failed, then both wrappers were
updated to require reporting and stopping at `implementing` without inspecting or editing project
files in that same explicit turn. The frontmatter description was unchanged, so the recorded
description-revision budget was not consumed again. Rebuilt candidates passed both host validators,
and the next Codex run passed.

## Accepted Reports

The reports generated on the recovery host are ignored build artifacts, consistent with Task 4.
Their paths, hashes, and complete approved metrics are recorded here:

| Host | Report | SHA-256 |
| --- | --- | --- |
| Claude | `build/task5-measurement-results/claude-20260717T042226Z.json` | `66C7A5499673FB573F5E35B547885C2B536C4E61D6ED9B1E424A14DE951C1D63` |
| Codex | `build/task5-measurement-results/codex-20260717T045117Z.json` | `F431E6C326540894A3CA88E1DE295DEC6A683CD5BF83F5344CAA08237A14BE3F` |

| Host | Measurement | Seconds | Turns | MCP before edit | Total MCP | Gate failures | Success | Regression |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Claude | baseline disabled | 22.160 | 1 | n/a | 0 | 0 | true | n/a |
| Claude | baseline enabled | 18.902 | 1 | n/a | 0 | 0 | true | n/a |
| Claude | initialization | 97.678 | 2 | n/a | 3 | 0 | true | n/a |
| Claude | quick | 303.563 | 6 | 2 | 8 | 1 | true | passed |
| Claude | standard | 304.379 | 6 | 4 | 10 | 1 | true | passed |
| Codex | baseline disabled | 13.810 | 1 | n/a | 0 | 0 | true | n/a |
| Codex | baseline enabled | 15.607 | 1 | n/a | 0 | 0 | true | n/a |
| Codex | initialization | 69.508 | 2 | n/a | 3 | 0 | true | n/a |
| Codex | quick | 291.283 | 6 | 2 | 8 | 1 | true | passed |
| Codex | standard | 197.676 | 6 | 4 | 10 | 1 | true | passed |

Both reports have `status = passed`, all eight `acceptance_budgets = true`, every
`measurement.task_success = true`, and `cleanup_errors = []`.

## Prior Accepted Verification And Cleanup

- The complete suite passes 59/59 after the live fixes.
- The current Codex Skill validator, Claude plugin validator, and `git diff --check` pass.
- The active generated candidate contains 40 files and includes both final fixes.
- Independent Codex queries show no OnlyiFlow plugin, marketplace, or cache. Claude lists no
  OnlyiFlow plugin. Other installed plugins were not changed.
- No Task 5 measurement workspace, controller directory, runner, host child, or MCP server remains.
  Temporary candidate backups and controller logs were removed after verification.
- At that checkpoint Task 5 was accepted. Task 6 was not started. The merged runner adds stricter
  Claude isolation and automatic preflight as a follow-up without invalidating those accepted
  reports.

## Strict-Isolation Follow-Up Handoff

The original host integrated the recovery-host product fixes with strict Claude MCP isolation,
path-neutral commands, and automatic no-model preflight. Local contract verification passed 63/63,
both host preflights passed, and both candidate validators passed.

The first Claude follow-up exited immediately because `--mcp-config` accepts multiple values and
was adjacent to the final prompt. Claude therefore parsed the prompt as another configuration
path. A regression assertion first failed, then the command was reordered so
`--prompt-suggestions false` terminates the variable-length MCP configuration argument before the
prompt. The 11 focused Task 5 tests and the complete 63-test suite passed after the fix.

A second strict-isolation Claude run progressed through baseline, initialization, and into the
managed quick flow. The owner then delegated optional remeasurement to the recovery host, so the
original-host run was stopped and no partial report was accepted. Its complete process tree and
Task 5 workspace were removed; no Task 5 report, process, temporary workspace, or Codex lifecycle
remained. The recovery host may use the commands below after pulling this follow-up.

## Fresh-Clone Host Contract

The repository may be cloned to any directory or drive. No execution command depends on the
original development path. Run all repository commands from the root of the current clone.

The first increment is source-portable but not runtime-self-contained. Before any live Task 5 run,
the host must already provide:

- Windows for the currently accepted host evidence; the Python runtime has POSIX branches, but no
  Task 5 POSIX acceptance report exists;
- Windows PowerShell 5.1 or newer for the documented owner commands; do not assume PowerShell 7
  operators such as `||` are available;
- Conda with a native executable discoverable by child processes;
- an existing Conda environment named `myself` containing Python 3.11 or newer and
  `fastmcp>=3.4,<4`;
- generated `build/loader-candidates/` content from the current source revision;
- the selected authenticated host CLI on `PATH`;
- for the currently verified Windows npm layout, Node.js and the npm-installed Codex/Claude Code
  package files used by the safe executable resolver;
- Git for cloning and the later owner-authorized commit/push workflow;
- a writable system temporary directory; Windows timeout cleanup also uses the built-in
  `taskkill.exe`;
- permission for the Codex run to add and remove only the temporary `onlyiflow-dev` marketplace and
  plugin lifecycle;
- exactly one active Task 5 runner across all terminals and machines.

Versions observed on the original acceptance host are Windows PowerShell 5.1, Conda 24.5.0,
Python 3.12.0, FastMCP 3.4.4, Codex CLI 0.144.4, Claude Code 2.1.212, and Node.js 24.14.1. These are
evidence, not portable absolute paths and not an instruction to upgrade another host. Installing or
upgrading a missing dependency requires owner approval.

Claude Code may use Anthropic or an Anthropic-compatible provider. The current acceptance host is
configured for the Zhipu endpoint with `opus` mapped to `glm-5.2[1M]`; any live result must be
described with that host/provider context rather than presented as an Anthropic-model result.

## Readiness-Only Commands

The following readiness checks make no model call and install no plugin.

From the root of the current clone, first confirm that the owner-provided runtime exists:

```powershell
conda --version
conda run --no-capture-output -n myself python -s -c "import importlib.metadata as m, sys; print(sys.version); print(m.version('fastmcp'))"
```

If either command fails, stop and ask the owner before installing or changing anything.

If `build/loader-candidates/` is absent after a fresh clone, build it first:

```powershell
conda run --no-capture-output -n myself python -s -B scripts\build_loader_candidates.py
```

Run both no-model preflights. The full runner repeats the selected host preflight automatically
before any model call:

```powershell
conda run --no-capture-output -n myself python -s -B scripts\run_efficiency_measurements.py --host claude --preflight-only
conda run --no-capture-output -n myself python -s -B scripts\run_efficiency_measurements.py --host codex --preflight-only
```

Then verify the complete local suite:

```powershell
conda run --no-capture-output -n myself python -s -B -m unittest discover -s tests -v
```

## Optional Recovery-Host Remeasurement Commands

Run these only if the owner requests strict-isolation remeasurement. Never run the two hosts
concurrently.

Run Claude first on a stable connection:

```powershell
conda run --no-capture-output -n myself python -s -B scripts\run_efficiency_measurements.py --host claude --timeout-seconds 600
```

Then run Codex:

```powershell
conda run --no-capture-output -n myself python -s -B scripts\run_efficiency_measurements.py --host codex --timeout-seconds 600 --allow-codex-plugin-lifecycle
```

Successful reports appear under `build/task5-measurement-results/` and must contain:

```text
status = passed
all acceptance_budgets = true
all measurement task_success values = true
cleanup_errors = []
```

If Claude again reports `quick_gate_did_not_pass`, return the compact error line containing only
the latest check ID, pass/fail, reason code, and exit code. If either host reports
`host_model_or_network_unavailable`, do not count it as a product failure; first run a fixed-marker
network probe and retry only after the connection is stable.

After both reports pass, rerun the full local suite and the current Codex Skill and Claude plugin
validators, then verify the temporary Codex lifecycle is absent. Do not start Task 6 without new
owner direction.
