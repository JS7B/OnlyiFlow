---
name: onlyiflow
description: Use only when the user explicitly invokes OnlyiFlow or explicitly asks to start, continue, check, or land an OnlyiFlow-managed flow. Manage explicit project-local workflow state with minimal risk-based ceremony and owner-controlled landing. Do not use for ordinary coding, planning, review, or generic workflow requests.
---

# OnlyiFlow

Keep this boundary:

> The host agent owns implementation. OnlyiFlow owns explicit workflow state and deterministic
> landing evidence.

## Start

1. Interpret the explicit request as `status`, `start`, `continue`, `check`, or `land`. If no action
   is stated, use `status`.
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
   the seven MCP tools.
4. Use the returned flow ID for every later tool call. If a flow is active, resume it and never call
   `flow_start` for another flow.
5. On a structured error, report its state and returned next action, then stop instead of guessing.

Treat an intermediate `next_action` as transition guidance, not as a stop condition. Unless the
request is status-only or reaches an explicit owner-turn boundary below, continue the permitted
tool sequence before reporting. For a managed quick start, call `project_status` and `flow_start`
in the same turn. For a complete managed standard start, continue through `flow_start`,
`spec_submit`, and `flow_claim` in the same turn.

After a managed start reaches `implementing`, report the state and stop. Do not inspect or edit
project files in that same explicit OnlyiFlow turn.

## Require owner turns

Never call `project_init` on the first unmanaged turn. Report the exact initialization entries,
ask whether to initialize this project, and stop. Only call `project_init` after a new owner
confirmation turn. Require the project to be unchanged. Then report the managed state with
`flow_start` as the one next action and stop.

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

## Advance the active flow

- `draft`: for `start` or `continue`, form one compact spec from the user's request and known
  project context. Use normal host inspection only when needed to identify honest expected files.
  If a required field is unknown, ask one compact clarification and stop. Otherwise call
  `spec_submit`, then `flow_claim`.
- `ready`: for `start` or `continue`, call `flow_claim`.
- `implementing`: leave exploration, editing, debugging, and test strategy to the host. Do not call
  `gate_run` unless the user explicitly asks to check or land.
- `gate_passed`: call `landing_request` only for an explicit `land` request.
- `waiting_owner`: report that the request is recorded and the owner controls external landing.

An explicit `check` is complete owner authorization to call `gate_run`. When `project_status`
returns an `implementing` flow, call `gate_run` in the same turn. Do not report, stop, ask a
question, or request confirmation between these calls.

For `check` or `land` while `implementing`, call `gate_run`. If a required check fails, remain in
`implementing`, report the compact evidence, and make fixing the failed checks the one next action.
If the gate passes for `check`, report `gate_passed` and make an explicit owner land request the one
next action. If the gate passes for `land`, call `landing_request`.

Call `landing_request` only after a passed gate. It records `waiting_owner`; it does not approve,
merge, push, create a pull request, or prevent direct Git commands.

## Stop

Report exactly one current state and one next action, then stop. Keep the report compact. Do not
echo commands, stdout, stderr, credentials, environment dumps, or external absolute paths.

Never create self-tracking TODOs, invoke another methodology Skill, spawn subagents, require a
worktree, or add subjective review loops. Do not install dependencies or plugins, edit Agent
configuration, or prescribe how the host implements the change.
