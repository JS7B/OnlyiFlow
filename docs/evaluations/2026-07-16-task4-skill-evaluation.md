# Task 4 Skill Evaluation

Date: 2026-07-16
Updated: 2026-07-17

Status: Complete; current Codex and Claude reports both pass 36/36

## Scope

The shared evaluation set is
`tests/fixtures/skill_evaluations.json`:

- 10 ordinary coding prompts that must make zero OnlyiFlow calls;
- 5 explicit prompts that must activate the Skill and reach the expected SQLite state;
- 3 objective high-risk prompts that must call `project_status`, recommend `deep`, request a new
  owner confirmation turn, and make no flow mutation.

Every case runs in a fresh temporary project and fresh host session. Enabled and disabled modes are
evaluated separately. The runner stores compact outcomes, tool names, durations, and project-state
snapshots; it does not store full transcripts.

Evaluation sessions use the host's low reasoning-effort setting. Triggering, tool availability,
state transitions, and stop boundaries do not require extended reasoning, and this prevents the
evaluation itself from dominating the product's ceremony budget.

## Owner Commands

Run from the current repository root:

```powershell
conda run --no-capture-output -n myself python -s -B scripts/run_skill_evaluations.py --host codex --mode both --timeout-seconds 600 --allow-codex-plugin-lifecycle
conda run --no-capture-output -n myself python -s -B scripts/run_skill_evaluations.py --host claude --mode both --timeout-seconds 600
```

The Codex command refuses to replace an existing `onlyiflow-dev` lifecycle. For enabled cases it
adds the local marketplace and candidate temporarily, then removes both in `finally`. The Claude
command uses `--plugin-dir` and installs nothing.

Each host has 36 expected results:

```text
passed = 36
failed = 0
infrastructure_error = 0
cleanup_errors = []
```

Reports are written under `build/task4-evaluation-results/`. Return the two report paths or the two
printed JSON summaries.

The runner stops after the first infrastructure error. A timeout, disconnected model stream, HTTP
5xx response, overload, or network failure is not counted as a Skill behavior failure; rerun that
host when the model connection is stable. An enabled explicit case also requires the exact real MCP
tool sequence from the fixture. Correct SQLite state without `mcp_tool_call` evidence fails, so a
host cannot pass by directly inspecting or mutating `.onlyiflow`.

## Current Evidence

- all 52 local tests pass;
- the Codex Skill validator passes;
- Claude plugin validation passes;
- ZCode Task 4 structural preflight passes;
- fixed candidates contain 40 files and match a clean rebuild byte-for-byte;
- the verified Codex Skill name is `$onlyiflow:onlyiflow`;
- the verified Claude namespaced command is `/onlyiflow:onlyiflow`;
- Claude report `claude-both-20260716T195242Z.json` records all 36 enabled/disabled cases passing,
  zero failures, zero infrastructure errors, and an empty cleanup-error list for the current Skill
  body.
- Codex report `codex-both-20260717T014407Z.json` records all 36 enabled/disabled cases passing,
  zero failures, zero infrastructure errors, and an empty cleanup-error list. Each enabled explicit
  case contains its exact real MCP call sequence, and the temporary plugin, marketplace, and cache
  were verified absent afterward.
- After the owner restarted Codex, a focused quick-start session on CLI 0.144.4 again exposed the
  deferred MCP tools and completed `project_status -> flow_start`. This is current runtime evidence;
  the earlier missing-tool reports below remain historical diagnostics rather than the acceptance
  state.
- Codex emits the same MCP item in both `item.started` and `item.completed`. The evaluator now
  ignores the lifecycle-start mirror, and a regression test proves that one real call is recorded
  once while preserving call order and repeated calls with distinct completed events.
- The evaluator sets `MCP_TIMEOUT=60000` so repeated fresh Claude sessions allow the conda-launched
  stdio server up to 60 seconds to initialize. A missing enabled `project_status` with no tool call
  and no state change is classified as an infrastructure error and stops the run.
- Claude report `claude-enabled-20260716T125009Z.json` records all five explicit cases passing.
- Claude report `claude-enabled-20260716T130629Z.json` records all three objective deep cases
  passing in their original sequential order.
- The first Claude quick-start attempt was denied by the host's `dontAsk` permission mode. The
  runner now grants only the exact seven namespaced OnlyiFlow tools through `--allowedTools`.
- A later deep attempt incorrectly preflighted MCP discovery and reported the server unavailable.
  The portable Skill contract now forbids probing or listing MCP servers, requires invoking
  `project_status` directly when exposed, permits one exact native tool search when it is deferred,
  and forbids direct `.onlyiflow` access.
- Historical Codex report `codex-disabled-20260716T095741Z.json` recorded a clean 180.898-second
  infrastructure timeout with zero tool calls, zero state mutation, and no cleanup error. A direct
  CLI probe then showed five WebSocket reconnect attempts and an HTTPS timeout before eventually
  returning the requested fixed marker, confirming transport instability rather than a Skill
  failure.
- Later Codex disabled-mode fixes use a read-only sandbox. A focused disabled case passed without
  state mutation, and a longer full attempt completed all 18 disabled cases before enabled-mode
  diagnosis began.
- The Codex plugin uses the current documented direct `.mcp.json` server map. A temporary install
  made `codex mcp get onlyiflow` report the cached stdio server as enabled, proving package loading
  and MCP configuration resolution.
- Historical enabled quick-start reports `codex-enabled-20260716T182720Z.json` and
  `codex-enabled-20260716T183520Z.json` both returned normally after about 131-137 seconds, recorded
  no `mcp_tool_call`, made no state mutation, and cleaned up with no error. The model reported that
  `project_status` was not exposed.
- A separate read-only `codex exec` prompt explicitly required the built-in tool search and
  `project_status` without loading the Skill. After WebSocket retries and HTTPS fallback, Codex
  again reported that neither tool was available and emitted no tool call. This separates the
  failure from Skill wording.
- Local CLI 0.144.4 reports `tool_search_always_defer_mcp_tools` as locked true. Official Codex
  issues describe the same regression class: MCP servers are enabled and discoverable but tools are
  absent from thread or tool-search surfaces.
- Codex 0.144.5 contains only a dangerous-command detection fix. It does not touch MCP discovery,
  deferred tools, or tool search, so upgrading to it is not a justified acceptance workaround.

The system `plugin-creator/scripts/validate_plugin.py` currently expects `.mcp.json` to contain a
Claude-style `mcpServers` wrapper. It therefore rejects the direct Codex server map even though the
Codex plugin lifecycle loads it and the 36-case report proves real calls. Keep the runtime-verified
format; use the foundation contract tests, Codex Skill validator, real lifecycle, and evaluation
report as the Codex acceptance evidence.

ZCode uses the same evaluation set during the later owner-assisted release smoke.
