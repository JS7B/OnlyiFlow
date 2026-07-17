# Task 5 Efficiency And Gate Value

Date: 2026-07-17

Status: Complete; accepted Claude and Codex reports pass every measurement and budget with no
cleanup error

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
- Managed quick must start with exactly `project_status -> flow_start` and no spec or plan.
- Managed standard must start with exactly `project_status -> flow_start -> spec_submit ->
  flow_claim` and exactly one compact spec.
- The Windows temporary-directory cleanup uses a verified system-temp root plus bounded retries.
  This avoids Python's recursive cleanup failure when a host child briefly retains its cwd.
- The final complete local suite passes all 59 tests, including the 7 focused Task 5 tests.

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
- a plugin-free, tool-free Claude fixed-marker probe then exceeded 120 seconds, confirming the
  current network/host connection was unsuitable for further measurement.

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

The repository was restored at `E:\onlyiflow` with clean `main` and `origin/main` both at
`6107ba850821283bc216f1d2a1342b03ec308c9a`. The generated loader candidates and the two accepted
Task 4 reports were restored from the old-machine handoff.

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

The local reports are ignored build artifacts, consistent with Task 4. Their paths, hashes, and
complete approved metrics are recorded here:

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

## Final Verification And Cleanup

- The complete suite passes 59/59 after the live fixes.
- The current Codex Skill validator, Claude plugin validator, and `git diff --check` pass.
- The active generated candidate contains 40 files and includes both final fixes.
- Independent Codex queries show no OnlyiFlow plugin, marketplace, or cache. Claude lists no
  OnlyiFlow plugin. Other installed plugins were not changed.
- No Task 5 measurement workspace, controller directory, runner, host child, or MCP server remains.
  Temporary candidate backups and controller logs were removed after verification.
- Task 5 is complete. Task 6 was not started.

## Reproduction Commands

Use the `myself` environment from `E:\onlyiflow`. Do not run the two hosts concurrently.

If `build/loader-candidates/` is absent after a fresh clone, build it first:

```powershell
conda run --no-capture-output -n myself python -s -B scripts\build_loader_candidates.py
```

Verify the local runner before spending model calls:

```powershell
conda run --no-capture-output -n myself python -s -B -m unittest discover -s tests -v
```

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
