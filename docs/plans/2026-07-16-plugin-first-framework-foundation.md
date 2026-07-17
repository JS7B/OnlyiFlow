# OnlyiFlow Plugin-First Framework Foundation Plan

Date: 2026-07-16

Status: Tasks 1 through 4 complete; Task 5 in progress, live measurement paused for stable network

## Goal

Build OnlyiFlow as a greenfield personal plugin whose portable contract is one manually invoked
Skill plus one deterministic local stdio MCP server.

The first release targets Codex, Claude Code, and ZCode. It does not install Hooks, edit Agent
configuration, observe Agent lifecycles, or recreate a mandatory development methodology.

## Binding Decisions

1. `D:\AgentX\OnlyiFlow_next` is the only implementation repository.
2. `D:\AgentX\OnlyiFlow` is read-only reference material. No merge, cherry-pick, or directory copy
   is allowed.
3. The repository is the source root; tested, isolated host candidates are the install roots.
4. The first portable product contains one Skill and one local MCP server.
5. The MCP surface contains exactly seven tools.
6. A managed quick flow reaches implementation with `project_status` then `flow_start`.
7. The MVP permits one non-terminal flow per project.
8. There is no Attention/event/review tool because the product intentionally collects no Agent
   events.
9. Human approval is outside model-callable MCP.
10. Codex and Claude loader proof precede workflow implementation. ZCode structural proof precedes
    implementation; final ZCode import and live smoke are owner-assisted release gates.

## Reuse Boundary

The old repository may inform a clean reimplementation of:

- risk names;
- explicit transition ideas;
- project-local SQLite state;
- deterministic gate execution;
- compact evidence;
- transport-independent runtime layering.

Do not reuse its source files or API compatibility layers for adapters, Hooks, observations,
Attention, event ingestion, platform probes, configuration ownership, generated settings, daemon,
or legacy MCP/CLI tools.

## Product Ceremony Budget

| Path | Before implementation | Before landing |
| --- | --- | --- |
| Existing managed `quick` | `project_status`, `flow_start` | `gate_run`, then `landing_request` if passed |
| Existing managed `standard` | `project_status`, `flow_start`, `spec_submit`, `flow_claim` | `gate_run`, one evidence-driven retry if needed, then `landing_request` |
| Existing managed `deep` | Owner confirmation, then standard state operations; native host planning only if approved | Gate evidence and owner-controlled landing |
| First project use | `project_status`, owner confirmation, `project_init`; measured separately | Same risk-specific path after setup |

## Task 0: Approve The Greenfield Documentation Baseline — Complete

**Files:**

- `AGENTS.md`
- `README.md`
- `docs/product-spec.md`
- `docs/engineering-spec.md`
- `docs/research/2026-07-16-three-host-loader-contract.md`
- this plan

1. Review the product, engineering, and loader boundaries.
2. Resolve any owner changes without creating implementation files.
3. After explicit owner approval, initialize Git if the owner wants this directory to become the
   canonical repository.
4. Commit the approved documentation baseline before loader code.

**Verify:** the baseline contains no copied old source, no implementation dependency, and no claim
that runtime work is already approved.

## Task 1: Prove The Loader And Real Runtime Import Path — Complete

Create disposable host-isolated candidates from the repository source with:

- one manual `onlyiflow-smoke` Skill;
- `ping`, `project_echo`, and `runtime_probe` tools;
- the minimum candidate metadata for Codex and Claude;
- a locally observed ZCode manifest candidate that is not imported automatically.

`runtime_probe` must use the exact future launcher and import the actual runtime package plus every
declared dependency. It must run after the host copies or caches the plugin and from a project path
containing spaces.

The bounded public-doc research is already complete. Do not extend Task 1 into general platform
research. Resolve only these executable unknowns:

1. whether Codex resolves `cwd: "."` and relative script arguments from its installed plugin cache;
2. which already-installed `myself` interpreter invocation works unchanged in Codex and Claude;
3. whether the locally observed ZCode manifest candidate passes read-only structural discovery;
4. whether `ToolResult(content=..., structured_content=..., is_error=...)` preserves the same
   response contract through both verified hosts.

Claude uses `${CLAUDE_PLUGIN_ROOT}`. The shared `server/stdio.py` derives the bundled `src` path from
`__file__`; business code never derives project root from current working directory.

Run the complete loader research contract for Codex and Claude. For ZCode:

- validate the candidate structure;
- use the embedded CLI only for read-only discovery;
- prepare an owner-importable directory;
- defer live import until the owner checkpoint.

**Gate:** Codex and Claude complete Skill discovery, explicit invocation, MCP initialize,
`tools/list`, `ping`, `project_echo`, `runtime_probe`, and unload. ZCode passes structural preflight.
If the gate fails, revise packaging only and stop before Task 2.

Recorded checkpoint on 2026-07-16:

- shared stdio protocol and copied paths-with-spaces tests pass;
- Claude Code completed ordinary non-trigger, explicit Skill invocation, all three MCP calls, and
  unload from a versioned path with spaces;
- Codex copied the plugin to its real cache and completed all three MCP calls from that cache;
- the owner confirmed Codex ordinary non-trigger and explicit `$onlyiflow-smoke` marker behavior in
  two independent fresh tasks;
- the disposable Codex plugin, marketplace, MCP registration, cache, and runtime processes were
  removed and verified absent;
- an independent post-removal Codex task confirmed both the Skill and MCP tools are unavailable;
- a clean candidate rebuild reproduced all 22 generated files byte-for-byte with no bytecode
  artifacts, and the full tests plus Codex/Claude validators passed after uninstall;
- ZCode read-only structure and CLI discovery pass; owner UI import remains a release gate;
- direct source-root import was rejected after Claude exposed duplicate resources; the checked-in
  builder now produces isolated Codex, Claude, and ZCode roots.

**Stop condition:** if Codex cannot locate the cached entry point without an undocumented absolute
cache path, or either host cannot invoke the approved existing Python environment without installing
anything, record `blocked` and write a distribution decision before any workflow implementation.

## Task 2: Create The Minimal Plugin And Python Skeleton — Complete

Create only the structure proven by Task 1:

```text
host manifests/configuration
skills/onlyiflow/SKILL.md
server/stdio.py
src/onlyiflow/
tests/
pyproject.toml
```

Requirements:

- keep all runtime source inside the imported/copied plugin root;
- use Python 3.11+;
- declare only dependencies approved by the owner;
- install nothing from the launcher or Skill;
- include no Hooks, agents, commands, monitors, LSP, apps, adapters, or daemon;
- add manifest and Skill validators where officially available.

**Verify:** the empty server starts through the same Codex and Claude launchers proven by Task 1,
and ZCode candidate metadata remains structurally valid.

Recorded checkpoint on 2026-07-16:

- all host manifests, the formal Skill, MCP server name, Python package, and project metadata use
  `onlyiflow` version `0.1.0`;
- `pyproject.toml` declares Python `>=3.11`, setuptools, and the already-installed FastMCP 3.x
  dependency without installing or upgrading anything;
- the server registers zero tools and starts through both proven Codex and Claude launchers from
  generated paths containing spaces;
- generated Codex, Claude, and ZCode roots are isolated, self-contained, contain
  `pyproject.toml`, and exclude smoke paths and bytecode;
- the Codex plugin validator, Codex Skill validator, Claude plugin validator, and ZCode structural
  checks pass;
- an isolated forward test loaded `$onlyiflow`, returned only the foundation status sentence, and
  called no tools;
- no Hooks, plugin-level agents, commands, monitors, LSP, apps, adapters, daemon, or workflow tools
  were added.

## Task 3: Implement The Seven-Tool Runtime Test-First — Complete

Implement in vertical slices:

1. `project_status` with a hard no-write unmanaged test.
2. `project_init` with exact layout and idempotency tests.
3. `flow_start` with atomic quick start and active-flow conflict tests.
4. `spec_submit` and `flow_claim` for standard/deep flows.
5. `gate_run` with configured commands, no-shell execution, timeouts, state transitions, and compact
   privacy-safe evidence.
6. `landing_request` with passed-gate enforcement and `waiting_owner` state.
7. MCP mapping with exact tool order, closed schemas, structured output, JSON text fallback, and
   tool-execution errors.

Tests must cover paths with spaces, invalid roots, malformed inputs, missing flows, invalid
transitions, concurrent starts, failed gates, passed gates, and absence of raw command data.

**Gate:** exact seven-tool `tools/list`; no approval or generic shell tool; complete unit and stdio
contract tests pass.

Recorded checkpoint on 2026-07-16:

- the transport-independent runtime implements the approved project, flow, spec, gate, and landing
  transitions with exactly the four approved SQLite tables;
- `project_status` is no-write for unmanaged projects, while `project_init` creates only the three
  approved `.onlyiflow/` entries and is idempotent;
- quick flows enter `implementing` atomically, standard/deep flows require one compact spec, and a
  database constraint plus concurrent-start tests enforce one non-terminal flow;
- configured gates run one to 32 tokenized checks without a shell, use bounded timeouts, discard raw
  output, and persist only compact evidence;
- `tools/list` exposes exactly the seven approved tools in deterministic order with closed, bounded
  input and output schemas;
- real copied-candidate stdio tests complete a standard flow through all seven tools, preserve
  structured success/error plus JSON text parity, and pass from paths containing spaces;
- all 32 automated tests pass, along with the Codex plugin validator, Codex Skill validator, Claude
  plugin validator, and ZCode structural preflight;
- two independently generated candidate trees contain 40 files and match byte-for-byte with no
  bytecode cache;
- the Skill remains an explicit fixed-status placeholder. Agent-facing workflow guidance and prompt
  activation evaluation remain Task 4, and ZCode Desktop import remains owner-assisted.

## Task 4: Implement And Evaluate The Single Skill — Complete

1. Implement the explicit-only invocation contract.
2. Implement the risk and ceremony budget from the product specification.
3. Make project initialization require a new owner confirmation turn.
4. Leave implementation strategy to the host.
5. Stop after reporting the current state and one next action.
6. Add static tests for prohibited behavior.
7. Build an evaluation set:
   - ten ordinary coding prompts that must not activate OnlyiFlow;
   - five explicit OnlyiFlow prompts that must activate it;
   - three explicit OnlyiFlow high-risk prompts where `deep` may be recommended only with objective
     evidence and owner confirmation.

Run evaluations in fresh Codex and Claude sessions with the plugin enabled and disabled. ZCode uses
the same set during the owner-assisted smoke.

**Gate:** zero activation on ordinary prompts; all explicit prompts load the Skill; at most one
description revision before returning for owner review.

Local checkpoint on 2026-07-16:

- the portable Skill implements explicit status/start/continue/check/land behavior, risk ceremony,
  separate owner turns for initialization and `deep`, gate/landing limits, and a one-state/one-action
  stop rule;
- Codex uses `$onlyiflow:onlyiflow`, while Claude uses `/onlyiflow:onlyiflow` with
  `disable-model-invocation: true`;
- static prohibitions and the 10 ordinary, 5 explicit, and 3 objective deep cases are checked into
  the test suite;
- `scripts/run_skill_evaluations.py` runs every case in a fresh temporary project and fresh host
  session, checks SQLite outcomes, separates enabled/disabled mode, stops on infrastructure failure,
  and cleans up the temporary Codex lifecycle;
- all 52 local tests, applicable host validators, ZCode structural preflight, and candidate reproducibility
  checks pass;
- Claude report `claude-both-20260716T195242Z.json` contains all 36 enabled/disabled passes, zero
  failures, zero infrastructure errors, and no cleanup error for the current Skill body;
- after the owner restarted Codex, CLI 0.144.4 again exposed the installed deferred MCP tools to
  `codex exec`; the focused quick-start case completed the exact `project_status -> flow_start`
  sequence and reached `implementing`;
- a runner regression test now proves that Codex `item.started` and `item.completed` mirrors count
  as one real MCP call rather than duplicate calls;
- Codex report `codex-both-20260717T014407Z.json` contains all 36 enabled/disabled passes, zero
  failures, zero infrastructure errors, and no cleanup error, and the temporary plugin,
  marketplace, and cache were verified absent afterward;
- the system plugin-creator validator still assumes a wrapped `.mcp.json` shape and is not used to
  override the direct server map proven by the real Codex lifecycle and evaluation report.

## Task 5: Measure Efficiency And Gate Value

For representative quick and standard flows record only:

- wall-clock time;
- model turns;
- MCP calls before the first code edit;
- total MCP calls;
- gate failures caught before landing;
- task success and regression result.

Acceptance budgets:

- enabled but uninvoked adds no MCP call or workflow turn;
- managed quick reaches implementation in two MCP calls;
- first-use initialization is reported separately;
- quick creates no spec or plan artifact;
- standard creates one compact spec;
- no flow enters an automatic review/reflection loop;
- gate evidence identifies at least one intentional failing-then-passing check without exposing raw
  output.

Remove any feature whose measured value does not justify its overhead.

Checkpoint on 2026-07-17:

- the test-first Task 5 runner measures paired disabled/enabled baseline, separate first-use
  initialization, managed quick, and managed standard scenarios;
- each representative flow verifies host-owned ordinary implementation, intentional regression
  injection, failed Gate evidence, ordinary repair, passing Gate, and owner-controlled landing;
- reports persist only the six approved metric groups plus acceptance booleans and cleanup status;
- the focused Task 5 suite passes all six tests, including Windows CLI argument and temporary
  cleanup regressions plus the deterministic failing-then-passing Gate fixture;
- live Claude and Codex runs were interrupted by the unstable model connection and then stopped at
  the owner's request; no partial report is accepted;
- all temporary processes, workspaces, Codex plugin, marketplace, and cache state were removed and
  verified absent;
- exact continuation commands and the remaining Gate diagnostic are recorded in
  `docs/evaluations/2026-07-17-task5-efficiency-and-gate-value.md`.

## Task 6: Three-Host Release Smoke

### Automated Codex And Claude Smoke

In disposable Git projects with spaces in their paths:

1. load the plugin through the proven temporary surface;
2. confirm one ordinary prompt produces no OnlyiFlow activity;
3. explicitly invoke OnlyiFlow;
4. initialize after owner-style confirmation;
5. complete one quick flow;
6. run one failing-then-passing configured gate;
7. request landing and confirm `waiting_owner`;
8. unload the plugin and confirm Skill and tools disappear.

### Owner-Assisted ZCode Smoke

Provide `build/loader-candidates/zcode/onlyiflow/` and the shared smoke instructions to the owner.
The owner imports it through ZCode Plugin Management using the local file/folder or marketplace surface,
runs the same behavioral scenario, and removes it through ZCode.

Automation may inspect read-only CLI/UI-visible results after the owner action, but does not perform
the import or lifecycle mutation.

**Gate:** all three hosts pass the same Skill and seven-tool semantics. Packaging may differ;
workflow semantics may not.

## Task 7: Documentation And Release Boundary

1. Replace research hypotheses with verified launcher instructions.
2. Document the smallest owner installation path for every host.
3. Document the ZCode owner-assisted lifecycle explicitly.
4. Document Python interpreter and dependency prerequisites without auto-install commands.
5. Document the limited enforcement boundary and external branch-protection recommendation.
6. Run the full formatter, linter, tests, manifest validators, prompt evaluations, and three-host
   smoke suite.

Release only after the owner approves the evidence and no test depends on the old repository.

## Final Acceptance Criteria

1. Reproducible host-specific candidates can be loaded or imported from the same repository source.
2. Codex, Claude Code, and ZCode expose the same manual `onlyiflow` Skill.
3. The same seven MCP tools and schemas are available in all hosts.
4. The real Python runtime import path passes after plugin copy/cache and with spaces in paths.
5. Ten ordinary prompts produce zero OnlyiFlow activation.
6. Managed quick work reaches implementation with two MCP calls and creates no spec or plan.
7. Standard work creates one compact spec before claim.
8. `project_status` on an unmanaged directory creates nothing.
9. Only one non-terminal flow is allowed per project.
10. Gate evidence contains no command, cwd, stdout, stderr, prompt, transcript, credential, or
    external absolute path.
11. No Hook, adapter, daemon, event collector, background monitor, subagent, or autonomous loop is
    present.
12. No model-callable approval tool exists.
13. The plugin performs no dependency installation or direct Agent-configuration write.
14. Owner-assisted ZCode import, smoke, disable/remove, and cleanup pass.
15. Documentation states that direct Git commands require external repository enforcement.
