# Three-Host Plugin Loader Research Contract

Date: 2026-07-16

Status: Task 1 complete; Codex and Claude verified; ZCode structural preflight complete

## Purpose

Prove how one repository source can build host-isolated plugins that expose the same manual Skill
and local stdio MCP server in Codex, Claude Code, and ZCode before workflow features are built.

This contract prevents a standalone `ping` success from being mistaken for proof that the real
Python runtime, dependencies, project root, or copied plugin can work.

## Public-Contract Freeze On 2026-07-16

The bounded web research is complete. More general research is not a prerequisite for the loader
spike. Remaining uncertainty is deliberately converted into runtime probes.

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

Local read-only inspection also confirmed FastMCP 3.4.3 in the `myself` environment. Its
`ToolResult` accepts `content`, `structured_content`, `meta`, and `is_error`, so the shared success
and structured-domain-error contract is implementable without replacing FastMCP or dropping MCP
error semantics.

### Frozen Launcher Strategy

Use one real entry point, `server/stdio.py`. After the host locates that file, the entry point must
derive its plugin root from its own resolved file path, prepend the bundled `src` directory, and
import the real package. Business code must never depend on process current directory.

Host configuration may differ only in how it locates the same entry point:

- Claude uses the documented `${CLAUDE_PLUGIN_ROOT}` substitution.
- Codex first tests plugin-root-relative `cwd` and arguments from the installed cache; absence of a
  documented MCP root variable is a probe result, not a reason to introduce an adapter.
- ZCode uses only the smallest candidate supported by the locally observed official manifest and
  is not called compatible until the owner-assisted UI gate passes.

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

## Candidate Artifact

The source builds three disposable, allowlisted candidates:

```text
generated host root
  one host manifest/configuration family
  one host-appropriate skills root
  server/stdio.py
  src/onlyiflow_smoke/
```

The repository root is deliberately not imported. Claude live proof showed that a universal source
tree duplicates root `skills/` and project `.mcp.json` alongside manifest-declared resources.

The Skill returns a fixed marker only when explicitly invoked.

The server exposes exactly:

| Tool | Purpose |
| --- | --- |
| `ping` | Prove initialize, tools/list, and tools/call. |
| `project_echo` | Return a normalized project basename, never an external absolute path. |
| `runtime_probe` | Import the exact future runtime package and every declared dependency, then return sanitized version families. |

`runtime_probe` must execute through the same interpreter, launcher, plugin-root resolution, and
copied package layout proposed for the real server.

## Shared Protocol Gate

For every host tested:

1. Record host version and selected surface.
2. Load the candidate using a documented or owner-approved local path.
3. Confirm the Skill is discoverable.
4. Confirm an ordinary small coding prompt does not invoke it.
5. Explicitly invoke the Skill and observe the fixed marker.
6. Start the MCP server.
7. Complete `initialize`.
8. Complete `tools/list` with the exact three tools.
9. Call `ping`.
10. Call `project_echo` from a project whose path contains spaces.
11. Call `runtime_probe` through the final import path.
12. Disable or unload the candidate through the host-owned lifecycle.
13. Confirm the Skill and tools are no longer exposed.
14. Record cleanup without retaining model content.

Codex and Claude must pass this gate before workflow runtime implementation. ZCode must pass the
structural/preflight portion before implementation and the owner-assisted live portion before
release.

## Codex Contract

Documented candidate surface:

```text
.codex-plugin/plugin.json
skills/
.mcp.json or a manifest-referenced MCP file
```

Research questions:

- What documented local marketplace or development path loads the generated candidate root?
- Does the host copy the plugin or use it in place?
- What variable or working directory identifies the copied plugin root?
- What project-root fact is available to the Skill and server?
- Can the selected `myself` Python interpreter be invoked with paths containing spaces?
- Does MCP approval policy prevent `ping` until the owner approves it?
- Does unload/remove eliminate both Skill and MCP exposure?

Codex accepted a disposable local marketplace and copied version `0.0.1` into its real plugin
cache. `cwd: "."` and `./server/stdio.py` resolved from that cache, and the exact three-tool protocol
passed there. Fresh-session Skill non-trigger, explicit invocation, and unload still require a new
Codex task because nested `codex exec` produced no model events in the active Desktop task.

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

Required behavior:

- load with `claude --plugin-dir <generated-claude-root>`;
- set `disable-model-invocation: true` on the smoke Skill;
- resolve bundled files through documented plugin-root substitution;
- use plugin-owned MCP configuration;
- never call `claude mcp add`;
- prove reload/unload behavior without modifying unrelated user configuration.

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

### Owner-Assisted Gate

When the Codex checkpoint is complete, provide `build/loader-candidates/zcode/onlyiflow/` to the
owner. The owner:

1. opens ZCode Plugin Management;
2. adds the local directory or local marketplace;
3. installs/enables the candidate;
4. confirms the Skill and MCP server are listed;
5. runs the shared non-trigger, explicit-trigger, `ping`, `project_echo`, and `runtime_probe` smoke;
6. disables or removes the candidate;
7. confirms both Skill and MCP exposure disappear.

If this gate fails, revise ZCode packaging only. Do not add Hooks, adapters, or ZCode-specific
workflow semantics.

## Exit Criteria

### Recorded Evidence On 2026-07-16

| Surface | Evidence | Result |
| --- | --- | --- |
| Shared package | `runtime_verified` | Seven automated checks pass, including a versioned cache-shaped path with spaces, exact three-tool order, structured/text parity, domain `is_error`, and path privacy. A clean rebuild reproduced all 22 generated files with identical SHA-256 hashes and no bytecode files. |
| Interpreter | `runtime_verified` | Python 3.12 in `myself`; FastMCP 3.4 and Pydantic 2.12 both report environment-owned dependency sources under `python -s`. |
| Codex cache/MCP | `runtime_verified` | CLI 0.144.4 copied version 0.0.1 to the real cache; plugin-relative cwd and all three tools passed from that cache. |
| Codex Skill invocation | `owner_verified` | Independent fresh tasks confirmed ordinary non-trigger and the exact `ONLYIFLOW_SMOKE_SKILL_V1` response for `$onlyiflow-smoke`. |
| Codex unload | `owner_verified` | Plugin and marketplace removal succeeded after plugin-owned MCP subprocess cleanup; installed/available entries, MCP registration, cache, and runtime process counts are all zero. An independent fresh task confirmed both Skill and MCP exposure are absent. |
| Claude Code | `runtime_verified` | CLI 2.1.211 passed one ordinary non-trigger, namespaced explicit Skill invocation, all three MCP calls with narrow tool allowlists, and unload from a versioned path with spaces. |
| ZCode | `locally_observed` | Desktop 3.3.6 / CLI 0.15.2; candidate structure passes tests, read-only plugins/skills/doctor return no diagnostics, and no lifecycle mutation occurred. |

The source-root hypothesis is rejected. `scripts/build_loader_candidates.py` is now the packaging
contract and produces isolated roots for all three hosts.

### Pending Codex Fresh-Task Checkpoint

The clean `onlyiflow@onlyiflow-loader-dev` lifecycle checkpoint is:

1. Complete: fresh task A confirmed an ordinary fixed-response prompt does not invoke OnlyiFlow.
2. Complete: fresh task B confirmed `$onlyiflow-smoke` returns exactly
   `ONLYIFLOW_SMOKE_SKILL_V1`.
3. Complete: the plugin and disposable marketplace were removed through the Codex CLI, with plugin
   entry, MCP registration, cache, and runtime process counts verified as zero.
4. Complete: fresh task C reported `skill_available=no` and `mcp_available=no`.

All four observations are recorded. The generated candidate remains in the repository for
reproducibility but is no longer installed.

The independent-task requirement was necessary because an active Codex task cannot refresh plugin
exposure mid-session. Task 1 now passes; Task 2 may begin only as a separate owner-directed goal.

### Task 1 Gate Result

`PASS`

Loader research is complete because:

- Codex is `runtime_verified` with owner-verified Skill invocation and unload;
- Claude Code is `runtime_verified`;
- ZCode structural preflight is complete;
- the exact selected Python/runtime strategy is recorded;
- copied-plugin paths with spaces work;
- no host required an OnlyiFlow Hook or direct Agent-config edit;
- owner-assisted ZCode live verification remains scheduled as a release gate.

If the real Python runtime cannot launch in Codex or Claude, stop before workflow implementation and
write a separate distribution decision. Do not solve the failure by rebuilding platform adapters.
