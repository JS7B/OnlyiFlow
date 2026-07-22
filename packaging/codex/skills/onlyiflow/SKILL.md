---
name: onlyiflow
description: Use only when the user explicitly invokes OnlyiFlow or explicitly asks to start, continue, check, land, or close an OnlyiFlow-managed flow. Manage explicit project-local workflow state with minimal risk-based ceremony and owner-controlled landing. Do not use for ordinary coding, planning, review, or generic workflow requests.
---

# OnlyiFlow

Keep this boundary:

> The host agent owns implementation. OnlyiFlow owns explicit workflow state and deterministic
> landing evidence.

## Start

1. Interpret the explicit request as `status`, `start`, `continue`, `check`, `land`, or `close`. If
   no action is stated, use `status`.
2. Resolve the current project directory explicitly. Pass the host's absolute current working
   directory to `project_status` exactly as provided; do not translate it to another path syntax
   or retry with a second path. Never select another project.
3. Call `project_status` exactly once at the start. Reuse that result during an immediate owner
   confirmation turn; do not call it a second time.
   Do not probe or list MCP servers. Invoke `project_status` directly when it is exposed. If
   `project_status` is absent from the initial tool list, do not report it unavailable. Use the
   host's native tool search exactly once for the literal query `project_status`, then invoke the
   returned tool.
   Never inspect or modify `.onlyiflow` directly; all workflow state reads and changes must use
   the twelve MCP tools.
4. Use the returned flow ID for every later tool call. If a flow is active, resume it and never call
   `flow_start` for another flow.
5. On a structured error, report its state and returned next action, then stop instead of guessing.

Treat an intermediate `next_action` as transition guidance, not as a stop condition. Unless the
request is status-only or reaches an explicit owner-turn boundary below, continue the permitted
tool sequence before reporting. For a managed quick start, call `project_status` and `flow_start`
in the same turn. For a complete managed direct standard start, continue through `flow_start`,
`spec_submit`, and `flow_claim` in the same turn.

After a managed start reaches `implementing`, report the state and stop. Do not inspect or edit
project files in that same explicit OnlyiFlow turn.

## Require owner turns

Never call `project_init` on the first unmanaged turn. Report the exact initialization entries,
ask whether to initialize this project, and stop. Only call `project_init` after a new owner
confirmation turn. Require the project to be unchanged. Then report the managed state with
`gate_configure` as the one next action and stop.

When a managed project's Gate is not configured, use ordinary host inspection only to identify the
project's existing verification commands. This normally occurs before the first flow, but can also
occur while resuming a flow created by an earlier OnlyiFlow version. Gate is the project's fixed
final quality check set. It runs only when the owner explicitly asks to `check` or `land`;
configuration stores the complete list and does not run commands, install dependencies, review
code, or perform Git operations. Present the proposed check IDs, required flags, commands, and
timeouts, then stop for owner confirmation. Never call
`gate_configure` before a new owner confirmation turn. After confirmation, call `gate_configure`
once and follow its returned next action. For a project with no active flow, report that the Gate
is ready and make `flow_start` the one next action. For an unconfigured legacy active flow, resume
the returned active-flow action. Never replace a configured Gate while a flow is active.

Choose the lowest justified risk:

- `quick`: narrow, localized, reversible work. Call `flow_start`; it enters `implementing`. Do not
  create a spec or plan.
- `standard`: normal feature or bug work with meaningful acceptance boundaries. Call `flow_start`,
  submit exactly one compact spec with `spec_submit`, then call `flow_claim`.
- `deep`: architecture changes, broad migrations, security-sensitive work, or failures with
  material cost. State the objective evidence, ask the owner to confirm `deep`, and stop before
  `flow_start`, extra planning, or approval ceremony. Continue only after a new confirmation turn.

Model uncertainty alone is not deep-risk evidence. Do not add ceremony merely because the agent is
unsure.

## Wave mode

Wave is an optional execution mode for one standard or deep Goal with multiple necessary work
packages. One Flow is still the only active Flow. `mode=wave` requires `risk=standard` or
`risk=deep`; `risk=quick` is invalid.

An explicit owner request for OnlyiFlow Wave counts as mode confirmation. Otherwise state the
objective dependency, conflict, or recovery evidence, ask whether to use Wave, and stop. Only after
the owner explicitly selects or confirms Wave mode, read `references/wave-workflow.md` once.

Start a confirmed Wave with `flow_start(mode="wave")` and the selected standard or deep risk.
Standard Wave selection does not add deep-risk confirmation ceremony. While the Flow is `draft`,
use ordinary host inspection to form the complete Goal, invariants, non-goals, work packages,
dependencies, Wave reasoning, scopes, acceptance, and authority boundaries. Then present the
complete Wave plan and stop for a new owner confirmation turn. Do not persist or execute a
proposed plan.

After plan confirmation, begin with `project_status`, call `spec_submit` for the top-level compact
spec, call `wave_plan_set` with the complete plan and returned revision, then call `flow_claim`.
Report `implementing` and stop before host implementation. Later `continue` turns follow the Wave
reference and the compact `wave_plan` summary. Never call `gate_run` for a Wave until the summary
reports no current Wave and its next action is `gate_run`.

## Advance the active flow

The state rules below apply only to `mode=direct`; they never route a Wave `draft` through the
direct spec-and-claim sequence or route an incomplete Wave to `gate_run`.

- `draft` in `mode=direct`: for `start` or `continue`, form one compact spec from the user's request and known
  project context. Use normal host inspection only when needed to identify honest expected files.
  If a required field is unknown, ask one compact clarification and stop. Otherwise call
  `spec_submit`, then `flow_claim`.
- `ready` in `mode=direct`: for `start` or `continue`, call `flow_claim`.
- `implementing` in `mode=direct`: leave exploration, editing, debugging, and test strategy to the
  host.
- `gate_passed` in `mode=direct`: call `landing_request` only for an explicit `land` request.
- `waiting_owner` in `mode=direct`: report that the request is recorded and the owner controls
  external landing.

For confirmed Wave flows, follow the Wave reference on explicit `continue`. Do not call `gate_run`
unless the user explicitly asks to check or land and all Wave packages are complete.

For a direct flow, an explicit `check` is complete owner authorization to call `gate_run`. When
`project_status` returns an `implementing` direct flow, call `gate_run` in the same turn. Do not
report, stop, ask a question, or request confirmation between these calls. For a Wave flow, first
require the compact summary to report implementation complete; otherwise report its package next
action instead of attempting the final Gate.

For `check` or `land` while a direct flow is `implementing`, call `gate_run`. If a required check fails, remain in
`implementing`, report the compact evidence, and make fixing the failed checks the one next action.
If the gate passes for `check`, report `gate_passed` and make an explicit owner land request the one
next action. If the gate passes for `land`, call `landing_request`.

Call `landing_request` only after a passed gate. It records `waiting_owner`; it does not approve,
merge, push, create a pull request, or prevent direct Git commands.

Before calling `flow_close`, present the Flow ID, current state, requested terminal result, and
reason code, then stop for a separate owner confirmation turn. Use `landed` with
`external_landing_completed` only from `waiting_owner`. Use `abandoned` from any nonterminal state
with exactly one of `owner_cancelled`, `goal_invalidated`, `scope_drifted`, or `goal_superseded`.

Call `flow_close` only after that confirmation. It records an already completed owner decision and
never runs Git, merges, pushes, or publishes. A closed Flow releases the active slot, so start the
next Flow without deleting `.onlyiflow`; the closed Flow and its history remain retained.

## Stop

Report exactly one current state and one next action, then stop. Keep the report compact. Do not
echo commands, stdout, stderr, credentials, environment dumps, or external absolute paths.

Outside confirmed Wave mode, never create self-tracking TODOs, invoke another methodology Skill,
spawn subagents, require a worktree, or add subjective review loops. In confirmed Wave mode the
host may use its native execution capabilities as described by the reference, but OnlyiFlow never
performs or controls them. Do not install dependencies or plugins or edit Agent configuration.
