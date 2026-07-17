# Three-Host Plugin Loader Research Contract

Date: 2026-07-16

Status: Task 1 complete; Task 6 live loader gate verified on Codex, Claude Code, and ZCode

## Purpose

Record how one repository source builds host-isolated plugins that expose the same manual Skill
and local stdio MCP server in Codex, Claude Code, and ZCode. The original loader questions are now
resolved by Tasks 1 through 6; this document preserves the verified launcher contract.

This contract prevents a standalone `ping` success from being mistaken for proof that the real
Python runtime, dependencies, project root, or copied plugin can work.

## Public-Contract Freeze On 2026-07-16

The bounded web research is complete. Every release-relevant loader uncertainty was converted into
a runtime or owner-assisted probe and is resolved below.

| Surface | Documented result | Consequence |
| --- | --- | --- |
| Codex plugin install | Local marketplace plugins are copied to `~/.codex/plugins/cache/<marketplace>/<plugin>/local/` and loaded from that copy. | Source-checkout success is insufficient; the installed cache copy must run. |
| Codex manifest | `skills` and `mcpServers` paths are plugin-root-relative and start with `./`; MCP configuration may be a direct server map or wrapped `mcp_servers` object. | Keep manifests and server source inside the repository/plugin root. |
| Codex root variables | Current public documentation explicitly assigns `PLUGIN_ROOT`, `PLUGIN_DATA`, and Claude-compatible aliases to plugin Hook commands. It does not make the same explicit promise for MCP subprocess configuration. | Do not treat a Codex MCP root variable as a contract. Probe relative `cwd` and script resolution from the installed cache. |
| Claude plugin paths | `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`, and `${CLAUDE_PROJECT_DIR}` are substituted in MCP configuration and exported to MCP subprocesses. | Use `${CLAUDE_PLUGIN_ROOT}` for the Claude launcher and keep project state outside the ephemeral plugin root. |
| Claude cache | Marketplace plugins are copied into a versioned local cache and cannot traverse outside the plugin directory. | Prove both disposable development loading and an installed/cache-shaped launch before accepting the package. |
| ZCode import | Public documentation supports custom marketplace sources from GitHub, Git URLs, and local paths, and identifies plugin-managed Skills and MCP servers. Plugin management remains Beta. | Treat the owner's folder/marketplace UI as authoritative; do not claim a stable public manifest or plugin-root variable. |
| MCP results | Structured output should also include serialized JSON text; business/domain failures are tool-execution errors with `isError: true`. | Preserve one response object in both content forms and signal correctable domain failure at the tool-result layer. |
| FastMCP stdio | Stdio is the default local transport and the client owns the child-process lifecycle. | No daemon, port, background service, or network listener is needed. |

Primary references:

- https://developers.openai.com/codex/plugins/build
- https://code.claude.com/docs/en/plugins-reference
- https://code.claude.com/docs/en/mcp
- https://zcode.z.ai/en/docs/plugin
- https://zcode.z.ai/en/docs/mcp-services
- https://modelcontextprotocol.io/specification/2025-11-25/server/tools
- https://gofastmcp.com/deployment/running-server
- https://gofastmcp.com/servers/tools

Local read-only inspection confirmed FastMCP 3.4.4 in the `myself` environment. Its
`ToolResult` accepts `content`, `structured_content`, `meta`, and `is_error`, so the shared success
and structured-domain-error contract is implementable without replacing FastMCP or dropping MCP
error semantics.

### Verified Launcher Instructions

Use one real entry point, `server/stdio.py`. After the host locates that file, the entry point must
derive its plugin root from its own resolved file path, prepend the bundled `src` directory, and
import the real package. Business code must never depend on process current directory.

Host configuration differs only in how it locates the same entry point:

- Codex loads `build/loader-candidates/codex-marketplace/` as a local marketplace, copies
  `onlyiflow` into its cache, and resolves `cwd: "."` plus `./server/stdio.py` from that copied
  plugin root. Explicit invocation is `$onlyiflow:onlyiflow`.
- Claude Code loads `build/loader-candidates/claude/onlyiflow/` with `--plugin-dir`, resolves the
  entry point through `${CLAUDE_PLUGIN_ROOT}`, and invokes `/onlyiflow:onlyiflow`.
- ZCode Desktop imports `build/loader-candidates/zcode/` as a local marketplace. Its root
  `marketplace.json` points to `./onlyiflow`, whose manifest resolves the entry point through
  `${ZCODE_PLUGIN_ROOT}`. Task 6 owner verification proved the same Skill and seven-tool runtime.

Task 1 selected `conda run --no-capture-output -n myself python -s` from already-installed tools.
The `-s` flag prevents user-site fallback; runtime probes confirmed that FastMCP and Pydantic load
from the `myself` environment. Paths with spaces and host cache/copy behavior pass without installing
or upgrading anything.

## Evidence Levels

| Level | Meaning |
| --- | --- |
| `documented` | A current public host document describes the capability. |
| `locally_observed` | This machine exposes the path, command, manifest, or UI behavior. |
| `runtime_verified` | The exact final launcher completed the required stdio protocol stages. |
| `owner_verified` | The owner completed a host UI action that automation must not perform. |
| `blocked` | A concrete host, policy, packaging, or runtime condition prevented proof. |

Configuration acceptance alone is not runtime verification. Skill discovery alone is not MCP
verification. A fixed server that bypasses the real runtime import path is not package verification.

## Privacy And Mutation Rules

Research records may contain:

- product and CLI versions;
- selected executable family;
- relative manifest locations;
- protocol stage names;
- Skill and tool names;
- sanitized reason codes;
- elapsed time and cleanup status.

Do not retain prompts, transcripts, model output, credentials, tokens, environment dumps, raw MCP
payloads, command output, or unrelated absolute paths.

Codex and Claude disposable development loading may be automated only through documented temporary
surfaces. ZCode plugin import, enable, disable, and removal remain owner-controlled unless the owner
later authorizes CLI mutation.

## Verified Candidate Artifact

The source builds three disposable, allowlisted candidates:

```text
generated host root
  one host manifest/configuration family
  one host-appropriate skills root
  server/stdio.py
  src/onlyiflow/
```

The repository root is deliberately not imported. Claude live proof showed that a universal source
tree duplicates root `skills/` and project `.mcp.json` alongside manifest-declared resources.

The current candidates contain 41 files, reproduce byte-for-byte, and expose the same explicit-only
Skill plus exactly these seven tools:

```text
project_status
project_init
flow_start
spec_submit
flow_claim
gate_run
landing_request
```

The copied candidates execute the real `onlyiflow` package and declared FastMCP dependency through
the final interpreter and entry point; no smoke-only package remains.

## Shared Release Gate

Every host passed the current release gate in a disposable Git project whose path contains spaces:

1. load the generated host candidate and expose one manual Skill plus seven tools;
2. answer an ordinary prompt with no OnlyiFlow activity;
3. explicitly inspect an unmanaged project without creating state;
4. initialize only in a new owner-confirmation turn;
5. start a quick flow at `implementing` with no spec;
6. leave implementation to the ordinary host agent;
7. record one failing and one passing configured Gate;
8. request landing and reach `waiting_owner`;
9. unload the plugin and confirm Skill/tool disappearance; and
10. remove temporary lifecycle state and runtime processes without retaining model content.

Claude and Codex are automated by `scripts/run_release_smoke.py`. ZCode uses the same behavioral
contract through the owner-controlled Desktop lifecycle.

## Codex Contract

Documented candidate surface:

```text
.codex-plugin/plugin.json
skills/
.mcp.json or a manifest-referenced MCP file
```

Verified behavior:

- `plugin marketplace add <codex-marketplace-root>` loads the local marketplace;
- `plugin add onlyiflow@onlyiflow-dev` copies version 0.1.0 into the real plugin cache;
- `cwd: "."` and `./server/stdio.py` resolve from that cache with paths containing spaces;
- a fresh task exposes `$onlyiflow:onlyiflow` and all seven MCP tools;
- lifecycle changes require a new task before model-visible exposure changes; and
- plugin then marketplace removal eliminates Skill, MCP, cache, and runtime exposure.

Allowed mutation: one disposable owner-approved local marketplace entry that is removed after the
spike. Do not edit Codex configuration files directly.

Public references:

- https://developers.openai.com/codex/plugins/build
- https://developers.openai.com/codex/concepts/customization

## Claude Code Contract

Documented candidate surface:

```text
.claude-plugin/plugin.json
skills-claude/
.mcp.claude.json
```

Verified behavior:

- load with `claude --plugin-dir <generated-claude-root>`;
- set `disable-model-invocation: true` on the manual Skill;
- resolve bundled files through documented plugin-root substitution;
- use plugin-owned MCP configuration;
- never call `claude mcp add`;
- unload by ending the session without modifying unrelated user configuration.

Public references:

- https://code.claude.com/docs/en/plugins
- https://code.claude.com/docs/en/plugins-reference
- https://code.claude.com/docs/en/skills
- https://code.claude.com/docs/en/mcp

## ZCode Contract

### Public And Owner-Provided Evidence

- ZCode documents plugin management as Beta.
- The public UI can add a marketplace from a GitHub repository, Git URL, file, or local directory.
- The owner-provided screenshot confirms the local file/folder selection surface on this machine.
- ZCode publicly documents external Skill and MCP import as compatibility paths.

Public references:

- https://zcode.z.ai/en/docs/plugin
- https://zcode.z.ai/en/docs/skill
- https://zcode.z.ai/en/docs/mcp-services

### Local Observations On 2026-07-16

| Fact | Evidence level | Value |
| --- | --- | --- |
| Desktop installation | `locally_observed` | ZCode 3.3.6 |
| Embedded CLI | `locally_observed` | `resources/glm/zcode.cjs` |
| CLI version | `locally_observed` | 0.15.2 |
| CLI runtime | `locally_observed` | Node v24.14.1 x64 on Windows |
| CLI discovery | `locally_observed` | `plugins list --json`, `skills list --json`, and `doctor --json` work |
| Plugin manifest location | `locally_observed` | `.zcode-plugin/plugin.json` in installed official plugins |
| Plugin contents | `locally_observed` | Skill roots and inline `mcpServers` are represented |
| Project/data variables | `locally_observed` | `${ZCODE_PROJECT_DIR}` and `${ZCODE_PLUGIN_DATA}` appear in an official installed plugin |
| Plugin-root substitution | `locally_observed` | Embedded CLI resolution handles `${ZCODE_PLUGIN_ROOT}` and the Claude-compatible plugin-root alias |

These local observations are not treated as a stable public standard. They authorize a disposable
candidate for owner testing, not an unattended installer or compatibility claim.

### Task 6 Current-Host Observations On 2026-07-17

The replacement machine differs from the original research host:

| Fact | Evidence level | Value |
| --- | --- | --- |
| Desktop installation | `locally_observed` | ZCode 3.3.1 |
| Embedded CLI | `locally_observed` | `D:\Zcode\resources\glm\zcode.cjs` |
| CLI version | `locally_observed` | 0.15.0 |
| Marketplace directory contract | `runtime_verified` | Add Marketplace requires root `marketplace.json` or `.claude-plugin/marketplace.json`; a lone `.zcode-plugin/plugin.json` is rejected |
| Plugin load | `owner_verified` | Local marketplace installation exposed the manual Skill and OnlyiFlow MCP server |
| Plugin unload | `owner_verified` | Plugin, Skill, and MCP exposure disappeared after owner removal |
| Marketplace retention | `locally_observed` | ZCode retained the owner-added local source and shows an uninstalled `获取` card; no visible removal control was found |
| Runtime cleanup | `locally_observed` | Uninstall left six orphaned OnlyiFlow MCP processes, which were terminated by exact command-line match |

The builder therefore emits `build/loader-candidates/zcode/marketplace.json` with one local source
entry for `./onlyiflow`. This is a packaging difference only; the plugin's Skill, seven-tool
runtime, and workflow semantics remain shared.

### Development Boundary

Automation may:

- invoke the embedded CLI for version, doctor, plugin list, and Skill list;
- validate candidate JSON against the locally observed minimal field set;
- prepare the generated ZCode-only folder for owner import;
- inspect exposure after the owner imports or removes it.

Automation must not, without later authorization:

- add a marketplace;
- import the folder;
- enable or disable the plugin;
- remove the plugin;
- edit `.zcode` user or workspace configuration.

### Verified Owner-Assisted Lifecycle

Task 6 provided `build/loader-candidates/zcode/` to the owner as a local marketplace root. Its
`marketplace.json` points to the self-contained `onlyiflow/` plugin. The owner:

1. opens ZCode Plugin Management;
2. adds that local marketplace root;
3. installs/enables the candidate;
4. confirms the Skill and MCP server are listed;
5. ran the shared ordinary-isolation, initialization, quick-flow, Gate, and landing smoke;
6. disables or removes the candidate;
7. confirms both Skill and MCP exposure disappear.

ZCode 3.3.1 retained the local marketplace as an uninstalled Discover source after step 6. The
owner accepted that host behavior because installed plugin, Skill, MCP, cache, workspace, and
runtime exposure were absent after cleanup.

## Exit Criteria

### Final Recorded Evidence Through 2026-07-17

| Surface | Evidence | Result |
| --- | --- | --- |
| Shared package | `runtime_verified` | Current candidates contain 41 files, reproduce byte-for-byte without bytecode, execute the real runtime from paths containing spaces, and expose exact seven-tool structured/text parity plus private Gate evidence. |
| Interpreter | `runtime_verified` | Python 3.12 in `myself`; FastMCP 3.4.4 and Pydantic 2.13.4 report environment-owned dependency sources under `python -s`. |
| Codex cache/MCP | `runtime_verified` | Desktop CLI 0.145.0-alpha.18 copied version 0.1.0 to the real cache; plugin-relative cwd and all seven tools passed from that cache. |
| Codex Skill invocation | `runtime_verified` | The current Task 4 enabled/disabled report passes all 36 ordinary, explicit, and deep cases for `$onlyiflow:onlyiflow`. |
| Codex unload | `owner_verified` | Plugin and marketplace removal succeeded after plugin-owned MCP subprocess cleanup; installed/available entries, MCP registration, cache, and runtime process counts are all zero. An independent fresh task confirmed both Skill and MCP exposure are absent. |
| Claude Code | `runtime_verified` | CLI 2.1.197 passes all 36 Task 4 cases and the Task 6 ordinary, initialization, quick-flow, Gate, landing, and unload sequence from paths containing spaces. |
| ZCode | `owner_verified` | Desktop 3.3.1 / CLI 0.15.0 on the replacement host loaded the generated local marketplace and passed ordinary isolation, explicit initialization, quick flow, failing/passing Gate, landing, and unload. Plugin, Skill, MCP exposure, and runtime processes are absent after cleanup; the owner intentionally retained only the uninstalled local marketplace source. |

The source-root hypothesis is rejected. `scripts/build_loader_candidates.py` is now the packaging
contract and produces isolated roots for all three hosts.

### Completed Codex Fresh-Task Checkpoint

The clean `onlyiflow@onlyiflow-dev` lifecycle checkpoint is:

1. Complete: fresh task A confirmed an ordinary fixed-response prompt does not invoke OnlyiFlow.
2. Complete: fresh tasks and current reports confirmed `$onlyiflow:onlyiflow` loads the manual
   Skill and model-visible tools.
3. Complete: the plugin and disposable marketplace were removed through the Codex CLI, with plugin
   entry, MCP registration, cache, and runtime process counts verified as zero.
4. Complete: fresh task C reported `skill_available=no` and `mcp_available=no`.

All four observations are recorded. The generated candidate remains in the repository for
reproducibility but is no longer installed.

The independent-task requirement remains necessary because an active Codex task cannot refresh
plugin exposure mid-session.

### Final Loader Result

`PASS`

The loader contract is complete because:

- Codex is `runtime_verified` with owner-verified Skill invocation and unload;
- Claude Code is `runtime_verified`;
- ZCode is owner-verified through live import, shared behavior, unload, and cleanup;
- the exact selected Python/runtime strategy is recorded;
- copied-plugin paths with spaces work;
- no host required an OnlyiFlow Hook or direct Agent-config edit.

The authoritative owner instructions are now in `docs/release-guide.md`. A future host regression
must produce a new bounded distribution decision; it must not be hidden behind platform adapters.
