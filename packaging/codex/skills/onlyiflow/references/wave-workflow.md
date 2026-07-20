# Wave workflow

Use this reference only for an owner-selected or owner-confirmed OnlyiFlow Wave. Do not load it for
direct quick, standard, or deep flows.

## Boundary

One Flow is one Goal; work packages are children, not additional active flows.

The host decides whether to use native subagents or worktrees. OnlyiFlow never creates, assigns,
interrupts, or removes them. The host also owns repository inspection, implementation, tests, diff
review, Git, external verification, and cleanup.

Plan confirmation does not authorize dependency installation, external writes, destructive
actions, Git operations, or release. Request new authority only when the work actually requires it.

Do not create self-tracking TODOs or reflection logs. Do not invoke another methodology Skill.
Do not require an independent reviewer unless the package contract requires one.

## Form the candidate plan

After the confirmed Wave starts in `draft`, inspect only the repository context needed to propose:

- one measurable Goal and final verification environment;
- invariants that every package must preserve;
- explicit non-goals;
- the complete set of necessary work packages;
- input and baseline assumptions that each package may rely on;
- dependencies and the evidence for each dependency;
- allowed and forbidden project-relative path scopes;
- deliverables, non-goals, acceptance assertions, and existing check IDs per package;
- runtime boundaries and still-required authorizations;
- whether a package requires independent review;
- an optional evidence condition whose false outcome is `deferred`;
- Wave assignments and why packages in the same Wave do not conflict.

A path ending in `/` is a directory scope. Other paths are exact files. Do not use available Agent
count to decide package count. Do not split implementation from its focused tests merely to create
more packages.

One package should have one primary result, be understandable without the full chat history, and
be independently handed off and reviewed. Avoid a package when its isolated result has no value or
must land atomically with another package.

A Wave is a dependency and conflict view, not a fixed sprint. Packages may share a Wave only when
there is no dependency path, declared write scopes are disjoint, interfaces are frozen, and the
host has checked runtime-resource compatibility.

Present the complete plan once. Include the Goal, invariants, non-goals, all packages, the dependency
DAG, Wave grouping, conflict evidence, acceptance, and authority boundaries. Stop for a separate
owner turn. Do not call `spec_submit` or `wave_plan_set` for an unconfirmed plan.

## Persist the confirmed plan

On the confirmation turn:

1. Call `project_status` exactly once first.
2. Reuse the returned Flow ID and Wave revision.
3. Call `spec_submit` with the compact top-level Goal contract.
4. Call `wave_plan_set` with the complete package list and exact expected revision.
5. Call `flow_claim`.
6. Report `implementing` and one next action, then stop before host implementation.

If plan validation reports a cycle, missing dependency, invalid Wave ordering, scope conflict, or
stale revision, present that evidence and stop. Never weaken the plan merely to make validation
pass.

## Continue the current Wave

Every later explicit OnlyiFlow turn starts with one `project_status`. Use its compact Wave summary;
do not request or repeat the full plan.

For a status-only request, report the current Wave, ready package IDs, attention package states, and
one next action. Do not start host work.

For an explicit `continue`:

1. Select only packages listed ready in the current Wave.
2. Use `work_package_status` to load only the target package.
3. Confirm that its dependencies are `integrated` and any required authority is already available.
4. Use `work_package_record(action="start")` only immediately before the host begins that package.
5. Give the host executor only the package contract, repository rules, baseline, invariants,
   authority, acceptance, and handoff format.
6. Let the host choose serial execution, native subagents, or isolated worktrees.
7. Do not let two host executors write the same worktree or declared path scope.
8. Record the resulting handoff only after the host action has occurred.

The host may execute multiple ready packages in the same Wave when its native capabilities and
resource limits allow. OnlyiFlow does not dispatch them. If the host uses no subagent, the primary
host may implement the package directly under the same contract.

## Package handoff and review

A submitted handoff contains only:

- package and attempt identity;
- base and head commit when Git authority exists;
- declared project-relative changed files;
- existing check IDs with pass/fail and compact reason codes;
- bounded known limits.

Never store command text, stdout, stderr, a full diff, prompts, chat history, credentials, external
absolute paths, or reasoning.

Use `work_package_record` only after the host action it records has occurred. Record:

- `submit` after implementation, declared checks, and handoff exist;
- `request_changes` after the host has found an in-scope blocking issue;
- `accept` after the host has reviewed the package against its contract;
- `integrate` only after the host has externally incorporated the submitted head commit;
- `interrupt` after a host execution attempt actually failed or was interrupted;
- `block` after a real authority, dependency, environment, or owner blocker exists;
- `resume` after that blocker is removed;
- `defer` only when the package's declared condition is false.

Only `integrated` packages satisfy dependencies. `submitted`, passing checks, or `accepted`
does not unlock downstream packages. Recording `integrate` does not ask OnlyiFlow to run or verify
Git; it records the host's completed external action.

Review is bounded. Read the package's complete relevant diff and acceptance evidence. If the
contract requires an independent reviewer, the host may use one read-only native reviewer. A
finding stays with the same package and existing scope. After a correction, recheck the finding and
related regression; do not restart a generic reflection cycle.

## Failure and reassignment

An executor failure is an attempt outcome, not package deletion.

After a real failure, the host inspects its own workspace and decides whether it can be reused.
Record `interrupt` with a compact reason and retryability. When known, include the base commit,
optional head commit, and declared project-relative changed files; do not include a diff or worker
conversation. If retryable, the package returns to `ready`; the next `start` increments the
attempt. A replacement executor receives the stable package contract and bounded handoff, not the
prior executor's full session.

Stop blind retries when the baseline, interface, scope, authority, or environment is no longer
valid. Record the package `blocked` and follow the replan boundary.

## Replan

Material scope, dependency, acceptance, authority, or Wave changes require a separately confirmed
replan. Interface changes and newly conflicting write scopes are also material.

Before proposing a replan, stop affected host work. Do not silently edit outside a package scope.
Show the current revision, evidence, retained integrated packages, replaced pending packages, and
the complete revised plan. Wait for a new owner turn.

After confirmation, call `project_status` first and use `wave_plan_set` with the complete revised
plan and exact current revision. Integrated package contracts are immutable. Executor replacement,
an in-scope fix, or focused review of an existing finding is not a replan.

## Final Gate and landing

When all current packages are `integrated` or correctly `deferred`, the Wave summary has no
current Wave and returns `gate_run` as the next action.

Do not call the final Gate earlier. On explicit `check` or `land`, run the existing project Gate
against the host's integrated main baseline. A failed Gate returns the Flow to implementation and
must be classified before fixing. Infrastructure failure is not automatically a product failure.

After a passed Gate, call `landing_request` only for explicit `land`. It records
`waiting_owner`; the host and owner retain commit, merge, push, release, and cleanup control.
