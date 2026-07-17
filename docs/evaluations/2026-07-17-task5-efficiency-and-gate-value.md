# Task 5 Efficiency And Gate Value

Date: 2026-07-17

Status: In progress; implementation and local tests pass, live host measurements paused for a
better network connection

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
- The complete local suite passes all 58 tests, including the 6 focused Task 5 tests.

## Interrupted Live Evidence

No Task 5 report is accepted yet.

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

## New-Window Commands

Use the `myself` environment from `D:\AgentX\OnlyiFlow_next`. Do not run the two hosts concurrently.

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
validators, verify the temporary Codex lifecycle is absent, then update Task 5 to complete. Do not
start Task 6 in the same goal.
