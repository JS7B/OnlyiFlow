# OnlyiFlow Product Specification

Date: 2026-07-16

Status: Normative specification for the OnlyiFlow 0.1.0 release candidate

## Product Definition

OnlyiFlow is a personal development-flow plugin for one owner who uses multiple coding agents
across multiple projects.

The shared product is:

```text
OnlyiFlow
  one manually invoked workflow Skill
  one deterministic local stdio MCP server
  one local project-state boundary
  thin host packaging for Codex, Claude Code, and ZCode
```

OnlyiFlow is not a coding agent or a methodology executor. It does not replace the host agent's
native ability to inspect a repository, reason about a change, edit code, run tests, or correct its
work.

Core rule:

> The host agent owns implementation. OnlyiFlow owns explicit workflow state and deterministic
> landing evidence.

## Target User

The target user is one AI full-stack developer who:

- uses Codex, Claude Code, and ZCode;
- wants the same small workflow state across those hosts;
- wants quick changes to remain quick;
- wants compact specs only when risk justifies them;
- wants deterministic checks before manually controlled landing;
- does not want an automatic methodology injected into every coding request.

## Product Goals

- Provide one explicit way to start or resume an OnlyiFlow-managed flow.
- Preserve host-agent freedom during implementation.
- Keep local state inspectable and project-scoped.
- Make quick, standard, and deep work observably different in ceremony.
- Run deterministic configured gates and return compact evidence.
- Keep human landing approval outside model-callable MCP tools.
- Behave consistently across Codex, Claude Code, and ZCode even when package metadata differs.
- Measure workflow overhead and remove features that do not improve state continuity or landing
  evidence.

## Explicit Non-Goals

The first increment does not provide:

- automatic Skill invocation for ordinary tasks;
- Hooks, event interception, transcript capture, or tool-call observation;
- adapter installation, status, ownership, rollback, or safe-uninstall frameworks;
- background monitors, daemons, resident services, or autonomous loops;
- automatic brainstorming, TODO creation, worktree creation, subagent dispatch, TDD orchestration,
  or reflection reviews;
- LLM calls or MCP sampling from the server;
- automatic dependency or plugin installation;
- user-level Agent configuration edits;
- a public marketplace release;
- host-level enforcement of direct Git commands.

## Invocation Contract

The `onlyiflow` Skill is manual-only.

Its description begins with:

> Use only when the user explicitly invokes OnlyiFlow or explicitly asks to start, continue, check,
> or land an OnlyiFlow-managed flow.

Generic requests such as "fix this bug", "implement the feature", "review this", or "make a plan"
must not activate OnlyiFlow.

Claude Code packaging must use its documented manual-invocation control. Codex and ZCode must use
the same explicit-only description and pass non-trigger evaluations; no unverified frontmatter is
added merely to imitate Claude behavior.

## Risk Levels

### quick

For narrow, low-risk work.

- No spec.
- No generated plan, TODO list, worktree, or review loop.
- In an already managed project, implementation begins after `project_status` and `flow_start`.
- `flow_start` atomically creates and claims the flow.

### standard

For normal features and bug fixes with meaningful acceptance boundaries.

- One compact spec: goal, acceptance, boundaries, and expected files.
- No second prose plan unless the owner asks.
- New-flow sequence: `project_status`, `flow_start`, `spec_submit`, `flow_claim`.

### deep

For architecture changes, broad migrations, security-sensitive work, or work whose failure has
material cost.

- The Skill explains the objective risk evidence.
- The owner must confirm before additional planning or approval ceremony.
- The host may use its own native plan mode after confirmation.
- OnlyiFlow does not spawn subagents or prescribe the host's reasoning mode.

Model uncertainty by itself is not evidence that work is deep.

## Project Initialization

`project_status` is always the first OnlyiFlow call and is read-only.

For an unmanaged project it returns:

- `managed: false`;
- the exact `.onlyiflow/` files that initialization would create;
- one next action requesting owner confirmation.

Only after confirmation may `project_init` create:

```text
<project>/.onlyiflow/
  onlyiflow.db
  config.toml
  specs/
```

Initialization is excluded from steady-state quick-flow latency measurements and is tested as a
separate first-use path.

## Flow Model

The MVP allows at most one non-terminal flow per managed project.

Core states:

```text
draft
ready
implementing
gate_passed
waiting_owner
landed        # reserved for a future owner-only surface
abandoned     # reserved for a future owner-only surface
```

Transitions:

```text
quick flow_start                 -> implementing
standard/deep flow_start         -> draft
spec_submit(draft)               -> ready
flow_claim(ready)                -> implementing
gate_run failure                 -> implementing
gate_run success                 -> gate_passed
landing_request(gate_passed)     -> waiting_owner
```

Starting another flow while one is non-terminal returns a structured conflict. The server never
guesses which flow is active.

## Gate And Landing Boundary

Gates run only configured deterministic checks. Public evidence contains:

```text
check_id
required
passed
reason_code
duration_ms
exit_code
```

It excludes command text, working-directory dumps, stdout, stderr, prompts, transcripts, and
credentials.

`landing_request` records that a passed flow is waiting for the owner. It does not approve, merge,
push, or create a pull request.

OnlyiFlow cannot prevent a direct Git command without an external enforcement mechanism. Product
documentation must state this limitation wherever landing safety is described.

## Portable MCP Surface

The first increment exposes exactly seven tools:

```text
project_status
project_init
flow_start
spec_submit
flow_claim
gate_run
landing_request
```

No approval, rejection, generic shell, event-recording, review-loop, plugin suggestion, daemon, or
adapter lifecycle tool is exposed.

## Success Measures

- Enabling the plugin without invoking it adds no MCP call and no workflow turn.
- Ten representative ordinary coding prompts produce zero OnlyiFlow activation.
- Five explicit OnlyiFlow prompts work in all three hosts.
- A managed quick flow reaches implementation in no more than two MCP calls.
- Quick creates no spec or planning artifact.
- Standard creates exactly one compact spec before claim.
- No successful flow enters an automatic review or reflection loop.
- Gate evidence catches a real failure before landing in the shared smoke scenario.
- The owner can disable or remove the exposed Skill and MCP server through the host-owned lifecycle.

## Release Boundary

Codex and Claude Code loader behavior may be automated during development. ZCode release acceptance
is owner-assisted: the owner imports the generated local marketplace through ZCode Desktop, runs
the shared smoke contract, and removes the installed plugin.

No release claim is allowed until all three hosts pass the same Skill and MCP behavior.
