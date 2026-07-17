# Task 7 Documentation And Release-Readiness Evidence

Date: 2026-07-17

Status: Complete. The normative documentation and package wording are formalized, and the local
verification matrix, reproducible packaging, fresh Codex and Claude Task 4/5/6 reports,
current-candidate ZCode focused delta smoke, and lifecycle cleanup all pass. All fifteen acceptance
criteria pass. The owner authorized the non-force corrective merge, direct `main` push, `v0.1.0`
tag, and GitHub Release on 2026-07-17; public plugin-marketplace publication remains excluded.

## Release Contract

Task 7 must:

1. replace research hypotheses with verified launch instructions;
2. document the smallest owner installation path for Codex, Claude Code, and ZCode;
3. document the owner-assisted ZCode lifecycle and retained uninstalled marketplace source;
4. freeze Python and dependency prerequisites without auto-install commands;
5. state that Git enforcement belongs to external CI, branch protection, or an owner-installed
   hook;
6. pass formatting, linting, tests, host validators, Task 4 prompt evaluations, Task 5 efficiency
   measurements, Task 6 release smokes, reproducible packaging, and lifecycle cleanup; and
7. audit all fifteen final acceptance criteria before requesting separate owner approval to commit,
   push, or release.

The owner installation and verification commands are in `docs/release-guide.md`. Passing automated
checks is evidence only; it is not release approval.

## Verified Environment And Launchers

The current evidence environment is:

- Python 3.12.0 in Conda environment `myself`;
- FastMCP 3.4.4 and Pydantic 2.13.4;
- Claude Code 2.1.197;
- Codex Desktop CLI 0.145.0-alpha.18, selected by the repository runner;
- working global npm Codex CLI 0.144.5, not mixed into the Task 7 reports;
- ZCode Desktop 3.3.1 with embedded CLI 0.15.0.

The global npm Codex platform package becoming available did not change OnlyiFlow or its generated
candidates. It only made a second host launcher usable. Task 7 keeps the previously verified
Desktop-native launcher for a consistent report lineage.

## Test-First Corrections During Verification

Task 7 exposed four bounded runner or Skill defects and corrected each test-first:

1. Python 3.12 `TemporaryDirectory` cleanup could recurse indefinitely on a transient Windows file
   lock. New tests first failed, then the runner moved to an explicit bounded cleanup with retry,
   compact WinError evidence, and reportable `cleanup_errors`.
2. Windows `taskkill` could itself time out while terminating a timed-out evaluation. The existing
   timeout regression and a new fallback test failed first; termination now falls back to a direct
   process signal without leaking the exception.
3. Claude sometimes treated an already explicit `check` as requiring another confirmation. A Skill
   contract assertion failed first. Both portable Skill wrappers now state that explicit `check` is
   complete owner authorization and forbid reporting or asking a question between `project_status`
   and `gate_run`. The frozen Skill description was not revised.
4. A transient Codex session reported in Chinese that `project_status` was not exposed. A new
   classification test first failed; the runner now classifies that exact host-tool condition as
   infrastructure rather than a product behavior failure.

## Local Verification

The current source and active candidates pass:

- `ruff format --check .`: 25 files formatted;
- `ruff check .`: all checks passed;
- complete unit suite: 71/71 passed;
- Codex Skill validator: passed;
- Claude plugin validator: passed;
- `git diff --check`: passed.

Two independent clean builds and `build/loader-candidates/` each contain 41 files. All relative
SHA-256 hashes match, there are zero differing bytes, and no `.pyc` or `.pyo` file exists. Both
temporary reproduction trees were removed.

## Post-Evidence Formalization

The final cleanup separates normative contracts from verification history. `docs/product-spec.md`,
`docs/engineering-spec.md`, and `docs/release-guide.md` contain no machine-specific path, Task
checkpoint, or observed host-version history. `README.md` identifies the repository layers and
keeps research, plans, evaluation records, and generated JSON reports explicitly non-normative.

The only generated-package byte changes after the accepted model-backed reports are the formal
package description in `pyproject.toml` and the package-module docstring in
`src/onlyiflow/__init__.py`, repeated for the three host candidates. No manifest, launcher, Skill,
MCP schema, workflow transition, Gate behavior, or dependency declaration changed. The rebuilt
candidate passed both host validators, the 71-test suite, real launcher integration tests, and two
independent 41-file reproducibility builds with zero byte difference and no compiled artifact.
The accepted model-backed reports therefore remain behavior evidence; the post-cleanup local checks
cover the two non-behavioral wording changes.

## Accepted Codex Evidence

| Gate | Accepted report | SHA-256 | Result |
| --- | --- | --- | --- |
| Task 4 | `build/task4-evaluation-results/codex-both-20260717T105603Z.json` | `B39455B522C0F7CF0C09F1C080B4E746A804064895FB60F4E6182DA3AB2D26E8` | 36/36 passed; 0 failed; 0 infrastructure error; `cleanup_errors = []` |
| Task 5 | `build/task5-measurement-results/codex-20260717T110428Z.json` | `C81D1A706128E931437ED21255C26631DAC9800C49C522D3BA20EBDB1E98A406` | `status = passed`; 8/8 budgets; 5/5 measurements successful; `cleanup_errors = []` |
| Task 6 | `build/task6-release-smoke-results/codex-20260717T111109Z.json` | `28615E609DBC691E4C110B7943F76B7B26EF84FCBC4EC700DD0F15B00BDE4899` | `status = passed`; 11/11 checks; `cleanup_errors = []` |

Independent checks after every Codex run found no OnlyiFlow plugin, development marketplace, cache,
Task workspace, or Task 4 evaluation directory. The runner never modified another plugin.

## Accepted Claude Evidence

After the earlier account limit reset, a repository-external, tool-free provider-aware probe
returned the exact `ONLYIFLOW_NETWORK_OK` marker in 3.185 seconds with exit code zero. The three
model-backed suites then ran sequentially, without Codex or ZCode model work in parallel.

| Gate | Accepted report | SHA-256 | Result |
| --- | --- | --- | --- |
| Task 4 | `build/task4-evaluation-results/claude-both-20260717T133513Z.json` | `773FA30E2A9A41E2924A6968A1635F53C0705FCE6DFCF65C4A4A70E3F07A67EB` | 36/36 passed; 0 failed; 0 infrastructure error; `cleanup_errors = []` |
| Task 5 | `build/task5-measurement-results/claude-20260717T134548Z.json` | `A40A17E967F3D6F3563E689498DDD4583ADB86CDA91097680897E728C0226D04` | `status = passed`; 8/8 budgets; 5/5 measurements successful; `cleanup_errors = []` |
| Task 6 | `build/task6-release-smoke-results/claude-20260717T135156Z.json` | `E95308AB88B2383345D5CAAF73377462DDEDEEBEED3610E84E262F1E892C82D9` | `status = passed`; 11/11 checks; `cleanup_errors = []` |

The superseded 29-pass Task 4 attempt remains infrastructure history only. The accepted reports
above contain the complete contracts and no infrastructure or cleanup error. Post-run inspection
found no Task temporary directory, test plugin, marketplace, cache, measurement process, or MCP
process.

## Fifteen-Criterion Audit

| # | Criterion | Current evidence | State |
| --- | --- | --- | --- |
| 1 | Reproducible host candidates | Active plus two fresh 41-file builds have zero byte difference | Pass |
| 2 | Same manual Skill in all hosts | Portable bodies are contract-tested equal; candidates contain the same explicit-only Skill | Pass |
| 3 | Same seven MCP tools and schemas | MCP contract and all three generated manifests expose the exact seven-tool server | Pass |
| 4 | Real copied runtime and paths with spaces | launcher contract, MCP integration, and fresh Codex/Claude Task 4 and Task 6 evidence | Pass |
| 5 | Ten ordinary prompts cause zero activation | fresh Codex and Claude Task 4 matrices | Pass |
| 6 | Quick start uses two calls and no spec/plan | runtime tests and fresh Codex/Claude Task 4/5/6 reports | Pass |
| 7 | Standard creates one compact spec | runtime tests and fresh Codex/Claude Task 4/5 reports | Pass |
| 8 | Unmanaged status is read-only | runtime test and Task 6 initialization boundary | Pass |
| 9 | One active flow maximum | sequential and concurrent conflict tests | Pass |
| 10 | Gate evidence is private and compact | Gate tests and Task 5 report contract | Pass |
| 11 | No prohibited autonomous feature | source/manifests contain only explicit non-goal or historical mentions | Pass |
| 12 | No model-callable approval tool | exact seven-tool schema excludes approval | Pass |
| 13 | No dependency install or Agent-config write | release documentation test and candidate audit | Pass |
| 14 | ZCode import, smoke, remove, cleanup | prior full smoke plus current-candidate focused delta, unload, and cleanup evidence | Pass |
| 15 | Git commands need external enforcement | release guide, product spec, and engineering spec state the boundary | Pass |

## Delivery Record

The final lifecycle inspection finds no installed OnlyiFlow plugin, Codex marketplace, versioned
cache, Task workspace, measurement process, or MCP process. It also removed the empty Claude
`onlyiflow-inline` plugin-data directory created during the verification window. The local
verification matrix remains green after the final documentation updates. The owner-accepted ZCode
Discover source is the only retained lifecycle state. It is uninstalled; after formalization its
12-file payload has the same paths as the active ZCode candidate and differs only in the two
non-behavioral wording files named above. The active generated candidate is the release source of
truth.

The validated release-candidate commit is
`95f1c6adb3b51f207c4f2d109f9ab903b15f97d9`. The owner-rejected remote commit
`8a539f2b8d1debb34b184f4682910ff30dbf863a` remains in history only. Non-force corrective merge
`0305d9e5c9bc0491bc30e5e25b72cf1097a6e068` has both commits as parents, and its tree hash
`0b0ceef72cea37f50dc83f1a082898f72d6381d9` exactly matches the validated candidate tree before
the merge. No rejected runner, test, or documentation content entered the release tree.

The GitHub release is `v0.1.0` in `JS7B/OnlyiFlow`. The owner authorization covers the direct
`main` delivery, tag, and GitHub Release only; it does not authorize publishing to a public plugin
marketplace.

Before the post-evidence wording cleanup, the owner refreshed the retained marketplace and installed
OnlyiFlow 0.1.0 through ZCode Desktop. Read-only inspection found exactly 12 files in the active
candidate and installed version cache, with no extra file and matching SHA-256 for every relative
path. The retained Discover payload also matched all 12 candidate files. In particular, the
candidate, marketplace, and installed Skill all had SHA-256
`3CDA084DC3BB4000E6985F9931497337EC9CDA82017A1C6E3533ED636D82A728`.

Task 6 already proved the complete ZCode ordinary-isolation, initialization, quick implementation,
failing-then-passing Gate, landing, unload, and cleanup lifecycle. The only post-Task-6 portable
behavior change was the Skill clarification that an explicit `check` authorizes immediate
`gate_run` without a second confirmation. Task 7 therefore repeated the changed boundary against
the exact current candidate instead of duplicating every unchanged owner turn:

- initialization created only the approved project state; before Gate configuration, the database
  was managed with no flow, spec, or Gate run;
- the current Skill started quick flow `4ec25ef60ab34f7692383882a9c90db3` directly in
  `implementing` with zero specs;
- one explicit `check` immediately ran `regression`, returned exit code 1, and left the flow in
  `implementing` without another confirmation;
- database evidence recorded exactly one failed Gate and only `check_id`, `passed`, `reason_code`,
  and `exit_code`; the privacy audit passed and the test file retained SHA-256
  `C7FF3D8F4355AD0B0527445C9E6EDF5858A3B96FB4A723CEA35E8CB0A000F941`; and
- after owner removal and ZCode shutdown, the installed version cache and registry entry were
  absent, no OnlyiFlow runtime process remained, and the accepted uninstalled Discover source was
  retained. The exact disposable Task 7 workspace was then removed.
