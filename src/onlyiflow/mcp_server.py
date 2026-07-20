from __future__ import annotations

import json
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.tools.base import ToolResult
from mcp.types import TextContent
from pydantic import WithJsonSchema

from .runtime import Runtime


mcp = FastMCP(name="OnlyiFlow", mask_error_details=True)
runtime = Runtime()

CONCISE_CONTRACT = """# OnlyiFlow concise contract

- Explicit invocation only.
- The host agent owns implementation. OnlyiFlow owns explicit workflow state and deterministic landing evidence.
- Start each explicit workflow turn with exactly one `project_status` call and follow the returned state.
- Owner confirmation is required before `project_init`, `gate_configure`, deep-flow ceremony, and a complete Wave plan.
- Wave mode is optional and deep-only. The host owns agents, worktrees, review, implementation, tests, and Git; OnlyiFlow records bounded plan/package state after host actions.

## State paths

- quick: `project_status -> flow_start -> implementing`
- standard/deep: `flow_start -> spec_submit -> flow_claim -> implementing`
- deep Wave: `flow_start(wave) -> spec_submit -> wave_plan_set -> flow_claim -> implementing`
- Wave completion: all packages `integrated` or validly `deferred` -> `gate_run`
- check pass: `implementing -> gate_run -> gate_passed`
- check fail: `implementing -> gate_run -> implementing`
- land: `gate_passed -> landing_request -> waiting_owner`

At most one non-terminal flow exists per project. At most one next action is reported.
Gate checks are deterministic. Landing remains owner-controlled.
This resource is static guidance, not project state. Use `project_status` for current state.
"""

ProjectRoot = Annotated[
    str,
    WithJsonSchema(
        {
            "type": "string",
            "minLength": 1,
            "description": "Existing project directory.",
        }
    ),
]
FlowId = Annotated[
    str,
    WithJsonSchema(
        {
            "type": "string",
            "pattern": "^[0-9a-f]{32}$",
            "description": "Stable OnlyiFlow flow identifier.",
        }
    ),
]
Risk = Annotated[
    str,
    WithJsonSchema(
        {
            "type": "string",
            "enum": ["quick", "standard", "deep"],
            "description": "Workflow risk level.",
        }
    ),
]
FlowMode = Annotated[
    str,
    WithJsonSchema(
        {
            "type": "string",
            "enum": ["direct", "wave"],
            "default": "direct",
            "description": "Direct flow or owner-confirmed Wave flow.",
        }
    ),
]
Title = Annotated[
    str,
    WithJsonSchema(
        {
            "type": "string",
            "minLength": 1,
            "maxLength": 200,
        }
    ),
]
SpecText = Annotated[
    str,
    WithJsonSchema(
        {
            "type": "string",
            "minLength": 1,
            "maxLength": 4000,
        }
    ),
]
ExpectedFiles = Annotated[
    list[str],
    WithJsonSchema(
        {
            "type": "array",
            "minItems": 1,
            "maxItems": 100,
            "uniqueItems": True,
            "items": {
                "type": "string",
                "minLength": 1,
                "maxLength": 512,
            },
        }
    ),
]
GateChecks = Annotated[
    list[dict[str, object]],
    WithJsonSchema(
        {
            "type": "array",
            "minItems": 1,
            "maxItems": 32,
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$",
                    },
                    "required": {"type": "boolean"},
                    "command": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 32,
                        "items": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 1024,
                        },
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 900,
                    },
                },
                "required": ["id", "required", "command", "timeout_seconds"],
                "additionalProperties": False,
            },
        }
    ),
]
PackageId = Annotated[
    str,
    WithJsonSchema(
        {
            "type": "string",
            "pattern": "^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$",
        }
    ),
]
ExpectedRevision = Annotated[
    int,
    WithJsonSchema({"type": "integer", "minimum": 0}),
]
PACKAGE_PATH_SCHEMA = {
    "type": "string",
    "minLength": 1,
    "maxLength": 512,
}
PACKAGE_TEXT_LIST_SCHEMA = {
    "type": "array",
    "minItems": 1,
    "maxItems": 32,
    "uniqueItems": True,
    "items": {"type": "string", "minLength": 1, "maxLength": 1000},
}
PACKAGES_SCHEMA = {
    "type": "array",
    "minItems": 1,
    "maxItems": 32,
    "items": {
        "type": "object",
        "properties": {
            "id": {
                "type": "string",
                "pattern": "^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$",
            },
            "slug": {
                "type": "string",
                "pattern": "^[a-z0-9][a-z0-9-]{0,63}$",
            },
            "title": {"type": "string", "minLength": 1, "maxLength": 200},
            "purpose": {"type": "string", "minLength": 1, "maxLength": 1000},
            "baseline_assumptions": PACKAGE_TEXT_LIST_SCHEMA,
            "wave": {"type": "integer", "minimum": 0, "maximum": 31},
            "dependencies": {
                "type": "array",
                "maxItems": 32,
                "uniqueItems": True,
                "items": {
                    "type": "string",
                    "pattern": "^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$",
                },
            },
            "allowed_paths": {
                "type": "array",
                "minItems": 1,
                "maxItems": 32,
                "uniqueItems": True,
                "items": PACKAGE_PATH_SCHEMA,
            },
            "forbidden_paths": {
                "type": "array",
                "maxItems": 32,
                "uniqueItems": True,
                "items": PACKAGE_PATH_SCHEMA,
            },
            "deliverables": PACKAGE_TEXT_LIST_SCHEMA,
            "non_goals": PACKAGE_TEXT_LIST_SCHEMA,
            "acceptance": PACKAGE_TEXT_LIST_SCHEMA,
            "check_ids": {
                "type": "array",
                "minItems": 1,
                "maxItems": 32,
                "uniqueItems": True,
                "items": {
                    "type": "string",
                    "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$",
                },
            },
            "runtime_boundaries": PACKAGE_TEXT_LIST_SCHEMA,
            "requires_authorization": {
                "type": "array",
                "maxItems": 8,
                "uniqueItems": True,
                "items": {
                    "type": "string",
                    "enum": [
                        "dependency_install",
                        "external_network",
                        "external_write",
                        "destructive_action",
                        "git_commit",
                        "git_merge",
                        "git_push",
                        "release",
                    ],
                },
            },
            "requires_independent_review": {"type": "boolean"},
            "condition": {
                "anyOf": [
                    {
                        "type": "object",
                        "properties": {
                            "evidence": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 1000,
                            },
                            "on_false": {"const": "deferred"},
                        },
                        "required": ["evidence", "on_false"],
                        "additionalProperties": False,
                    },
                    {"type": "null"},
                ]
            },
        },
        "required": [
            "id",
            "slug",
            "title",
            "purpose",
            "baseline_assumptions",
            "wave",
            "dependencies",
            "allowed_paths",
            "forbidden_paths",
            "deliverables",
            "non_goals",
            "acceptance",
            "check_ids",
            "runtime_boundaries",
            "requires_authorization",
            "requires_independent_review",
            "condition",
        ],
        "additionalProperties": False,
    },
}
Packages = Annotated[list[dict[str, object]], WithJsonSchema(PACKAGES_SCHEMA)]
PackageAction = Annotated[
    str,
    WithJsonSchema(
        {
            "type": "string",
            "enum": [
                "start",
                "submit",
                "request_changes",
                "accept",
                "integrate",
                "interrupt",
                "block",
                "resume",
                "defer",
            ],
        }
    ),
]
Commit = Annotated[
    str,
    WithJsonSchema({"type": "string", "pattern": "^[0-9a-f]{7,64}$"}),
]
ChangedFiles = Annotated[
    list[str],
    WithJsonSchema(
        {
            "type": "array",
            "minItems": 1,
            "maxItems": 32,
            "uniqueItems": True,
            "items": PACKAGE_PATH_SCHEMA,
        }
    ),
]
PACKAGE_CHECK_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "check_id": {
            "type": "string",
            "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$",
        },
        "passed": {"type": "boolean"},
        "reason_code": {
            "type": "string",
            "pattern": "^[a-z0-9][a-z0-9_]{0,63}$",
        },
    },
    "required": ["check_id", "passed", "reason_code"],
    "additionalProperties": False,
}
PackageChecks = Annotated[
    list[dict[str, object]],
    WithJsonSchema(
        {
            "type": "array",
            "minItems": 1,
            "maxItems": 32,
            "items": PACKAGE_CHECK_INPUT_SCHEMA,
        }
    ),
]
KnownLimits = Annotated[
    list[str],
    WithJsonSchema(
        {
            "type": "array",
            "maxItems": 8,
            "uniqueItems": True,
            "items": {"type": "string", "minLength": 1, "maxLength": 500},
        }
    ),
]
ReasonCode = Annotated[
    str,
    WithJsonSchema({"type": "string", "pattern": "^[a-z0-9][a-z0-9_]{0,63}$"}),
]

READ_ONLY = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}
IDEMPOTENT_MUTATION = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}
MUTATION = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": False,
    "openWorldHint": False,
}

TOOL_NAMES = [
    "project_status",
    "project_init",
    "gate_configure",
    "flow_start",
    "spec_submit",
    "wave_plan_set",
    "flow_claim",
    "work_package_status",
    "work_package_record",
    "gate_run",
    "landing_request",
]
NEXT_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {"type": "string", "enum": TOOL_NAMES},
        "reason_code": {
            "type": "string",
            "pattern": "^[a-z0-9_]+$",
            "maxLength": 64,
        },
    },
    "required": ["tool", "reason_code"],
    "additionalProperties": False,
}
ERROR_SCHEMA = {
    "type": "object",
    "properties": {
        "code": {
            "type": "string",
            "pattern": "^[a-z0-9_]+$",
            "maxLength": 64,
        },
        "message": {"type": "string", "minLength": 1, "maxLength": 500},
        "retryable": {"type": "boolean"},
    },
    "required": ["code", "message", "retryable"],
    "additionalProperties": False,
}
FLOW_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "pattern": "^[0-9a-f]{32}$"},
        "risk": {"type": "string", "enum": ["quick", "standard", "deep"]},
        "mode": {"type": "string", "enum": ["direct", "wave"]},
        "title": {"type": "string", "minLength": 1, "maxLength": 200},
        "state": {
            "type": "string",
            "enum": [
                "draft",
                "ready",
                "implementing",
                "gate_passed",
                "waiting_owner",
            ],
        },
        "created_at": {"type": "string", "minLength": 1, "maxLength": 64},
        "updated_at": {"type": "string", "minLength": 1, "maxLength": 64},
    },
    "required": [
        "id",
        "risk",
        "mode",
        "title",
        "state",
        "created_at",
        "updated_at",
    ],
    "additionalProperties": False,
}
CHECK_SCHEMA = {
    "type": "object",
    "properties": {
        "check_id": {
            "type": "string",
            "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$",
        },
        "required": {"type": "boolean"},
        "passed": {"type": "boolean"},
        "reason_code": {
            "type": "string",
            "enum": [
                "check_passed",
                "check_failed",
                "check_timeout",
                "check_launch_error",
            ],
        },
        "duration_ms": {"type": "integer", "minimum": 0},
        "exit_code": {
            "anyOf": [
                {"type": "integer"},
                {"type": "null"},
            ]
        },
    },
    "required": [
        "check_id",
        "required",
        "passed",
        "reason_code",
        "duration_ms",
        "exit_code",
    ],
    "additionalProperties": False,
}
CHECKS_SCHEMA = {
    "type": "array",
    "items": CHECK_SCHEMA,
    "minItems": 1,
    "maxItems": 32,
}
INITIALIZATION_ENTRIES_SCHEMA = {
    "type": "array",
    "items": {
        "type": "string",
        "enum": [
            ".onlyiflow/onlyiflow.db",
            ".onlyiflow/config.toml",
            ".onlyiflow/specs/",
        ],
    },
    "minItems": 3,
    "maxItems": 3,
    "uniqueItems": True,
}
SPEC_SCHEMA = {
    "type": "object",
    "properties": {
        "goal": {"type": "string", "minLength": 1, "maxLength": 4000},
        "acceptance": {"type": "string", "minLength": 1, "maxLength": 4000},
        "boundaries": {"type": "string", "minLength": 1, "maxLength": 4000},
        "expected_files": {
            "type": "array",
            "items": {"type": "string", "minLength": 1, "maxLength": 512},
            "minItems": 1,
            "maxItems": 100,
            "uniqueItems": True,
        },
    },
    "required": ["goal", "acceptance", "boundaries", "expected_files"],
    "additionalProperties": False,
}
LATEST_GATE_SCHEMA = {
    "type": "object",
    "properties": {
        "flow_id": {"type": "string", "pattern": "^[0-9a-f]{32}$"},
        "passed": {"type": "boolean"},
        "checks": CHECKS_SCHEMA,
    },
    "required": ["flow_id", "passed", "checks"],
    "additionalProperties": False,
}
GATE_CONFIG_STATUS_SCHEMA = {
    "type": "object",
    "properties": {
        "configured": {"type": "boolean"},
        "check_count": {"type": "integer", "minimum": 0, "maximum": 32},
        "required_count": {"type": "integer", "minimum": 0, "maximum": 32},
    },
    "required": ["configured", "check_count", "required_count"],
    "additionalProperties": False,
}
GATE_CONFIGURED_CHECK_SCHEMA = {
    "type": "object",
    "properties": {
        "check_id": {
            "type": "string",
            "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$",
        },
        "required": {"type": "boolean"},
        "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 900},
    },
    "required": ["check_id", "required", "timeout_seconds"],
    "additionalProperties": False,
}
PACKAGE_STATUS_VALUES = [
    "proposed",
    "ready",
    "running",
    "submitted",
    "changes_requested",
    "accepted",
    "integrated",
    "blocked",
    "deferred",
]
PACKAGE_STATUS_COUNTS_SCHEMA = {
    "type": "object",
    "properties": {
        status: {"type": "integer", "minimum": 1, "maximum": 32}
        for status in PACKAGE_STATUS_VALUES
    },
    "additionalProperties": False,
}
ATTENTION_PACKAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "package_id": {
            "type": "string",
            "pattern": "^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$",
        },
        "status": {
            "type": "string",
            "enum": [
                "running",
                "submitted",
                "changes_requested",
                "accepted",
                "blocked",
            ],
        },
        "attempt_count": {"type": "integer", "minimum": 0},
    },
    "required": ["package_id", "status", "attempt_count"],
    "additionalProperties": False,
}
WAVE_PLAN_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "flow_id": {"type": "string", "pattern": "^[0-9a-f]{32}$"},
        "configured": {"type": "boolean"},
        "revision": {"type": "integer", "minimum": 0},
        "package_count": {"type": "integer", "minimum": 0, "maximum": 32},
        "current_wave": {
            "anyOf": [
                {"type": "integer", "minimum": 0, "maximum": 31},
                {"type": "null"},
            ]
        },
        "ready_packages": {
            "type": "array",
            "maxItems": 32,
            "uniqueItems": True,
            "items": {
                "type": "string",
                "pattern": "^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$",
            },
        },
        "attention_packages": {
            "type": "array",
            "maxItems": 32,
            "items": ATTENTION_PACKAGE_SCHEMA,
        },
        "status_counts": PACKAGE_STATUS_COUNTS_SCHEMA,
    },
    "required": [
        "flow_id",
        "configured",
        "revision",
        "package_count",
        "current_wave",
        "ready_packages",
        "attention_packages",
        "status_counts",
    ],
    "additionalProperties": False,
}
PACKAGE_CHECK_OUTPUT_SCHEMA = PACKAGE_CHECK_INPUT_SCHEMA
WORK_PACKAGE_SCHEMA = {
    "type": "object",
    "properties": {
        **PACKAGES_SCHEMA["items"]["properties"],
        "revision": {"type": "integer", "minimum": 1},
        "status": {"type": "string", "enum": PACKAGE_STATUS_VALUES},
        "attempt_count": {"type": "integer", "minimum": 0},
        "base_commit": {
            "anyOf": [
                {"type": "string", "pattern": "^[0-9a-f]{7,64}$"},
                {"type": "null"},
            ]
        },
        "head_commit": {
            "anyOf": [
                {"type": "string", "pattern": "^[0-9a-f]{7,64}$"},
                {"type": "null"},
            ]
        },
        "changed_files": {
            "type": "array",
            "maxItems": 32,
            "uniqueItems": True,
            "items": PACKAGE_PATH_SCHEMA,
        },
        "checks": {
            "type": "array",
            "maxItems": 32,
            "items": PACKAGE_CHECK_OUTPUT_SCHEMA,
        },
        "known_limits": {
            "type": "array",
            "maxItems": 8,
            "uniqueItems": True,
            "items": {"type": "string", "minLength": 1, "maxLength": 500},
        },
        "reason_code": {
            "anyOf": [
                {
                    "type": "string",
                    "pattern": "^[a-z0-9][a-z0-9_]{0,63}$",
                },
                {"type": "null"},
            ]
        },
    },
    "required": [
        *PACKAGES_SCHEMA["items"]["required"],
        "revision",
        "status",
        "attempt_count",
        "base_commit",
        "head_commit",
        "changed_files",
        "checks",
        "known_limits",
        "reason_code",
    ],
    "additionalProperties": False,
}


def response_schema(data_schema: dict) -> dict:
    return {
        "type": "object",
        "oneOf": [
            {
                "type": "object",
                "properties": {
                    "ok": {"const": True},
                    "data": data_schema,
                    "next_action": NEXT_ACTION_SCHEMA,
                },
                "required": ["ok", "data"],
                "additionalProperties": False,
            },
            {
                "type": "object",
                "properties": {
                    "ok": {"const": False},
                    "error": ERROR_SCHEMA,
                    "next_action": NEXT_ACTION_SCHEMA,
                },
                "required": ["ok", "error"],
                "additionalProperties": False,
            },
        ],
    }


PROJECT_STATUS_OUTPUT = response_schema(
    {
        "oneOf": [
            {
                "type": "object",
                "properties": {
                    "managed": {"const": False},
                    "initialization_entries": INITIALIZATION_ENTRIES_SCHEMA,
                },
                "required": ["managed", "initialization_entries"],
                "additionalProperties": False,
            },
            {
                "type": "object",
                "properties": {
                    "managed": {"const": True},
                    "active_flow": {
                        "anyOf": [FLOW_SCHEMA, {"type": "null"}],
                    },
                    "latest_gate": {
                        "anyOf": [LATEST_GATE_SCHEMA, {"type": "null"}],
                    },
                    "gate_config": GATE_CONFIG_STATUS_SCHEMA,
                    "wave_plan": {
                        "anyOf": [WAVE_PLAN_SUMMARY_SCHEMA, {"type": "null"}],
                    },
                },
                "required": [
                    "managed",
                    "active_flow",
                    "latest_gate",
                    "gate_config",
                    "wave_plan",
                ],
                "additionalProperties": False,
            },
        ]
    }
)
PROJECT_INIT_OUTPUT = response_schema(
    {
        "type": "object",
        "properties": {
            "created": {"type": "boolean"},
            "entries": INITIALIZATION_ENTRIES_SCHEMA,
        },
        "required": ["created", "entries"],
        "additionalProperties": False,
    }
)
GATE_CONFIGURE_OUTPUT = response_schema(
    {
        "type": "object",
        "properties": {
            "checks": {
                "type": "array",
                "items": GATE_CONFIGURED_CHECK_SCHEMA,
                "minItems": 1,
                "maxItems": 32,
            },
            "check_count": {"type": "integer", "minimum": 1, "maximum": 32},
            "required_count": {"type": "integer", "minimum": 0, "maximum": 32},
        },
        "required": ["checks", "check_count", "required_count"],
        "additionalProperties": False,
    }
)
FLOW_START_OUTPUT = response_schema(
    {
        "type": "object",
        "properties": {"flow": FLOW_SCHEMA},
        "required": ["flow"],
        "additionalProperties": False,
    }
)
SPEC_SUBMIT_OUTPUT = response_schema(
    {
        "type": "object",
        "properties": {
            "flow_id": {"type": "string", "pattern": "^[0-9a-f]{32}$"},
            "state": {"const": "ready"},
            "spec": SPEC_SCHEMA,
        },
        "required": ["flow_id", "state", "spec"],
        "additionalProperties": False,
    }
)
WAVE_PLAN_SET_OUTPUT = response_schema(WAVE_PLAN_SUMMARY_SCHEMA)
FLOW_CLAIM_OUTPUT = FLOW_START_OUTPUT
WORK_PACKAGE_STATUS_OUTPUT = response_schema(
    {
        "type": "object",
        "properties": {
            "flow_id": {"type": "string", "pattern": "^[0-9a-f]{32}$"},
            "package": WORK_PACKAGE_SCHEMA,
        },
        "required": ["flow_id", "package"],
        "additionalProperties": False,
    }
)
WORK_PACKAGE_RECORD_OUTPUT = response_schema(
    {
        "type": "object",
        "properties": {
            "flow_id": {"type": "string", "pattern": "^[0-9a-f]{32}$"},
            "package": WORK_PACKAGE_SCHEMA,
            "wave_plan": WAVE_PLAN_SUMMARY_SCHEMA,
        },
        "required": ["flow_id", "package", "wave_plan"],
        "additionalProperties": False,
    }
)
GATE_RUN_OUTPUT = response_schema(
    {
        "type": "object",
        "properties": {
            "flow_id": {"type": "string", "pattern": "^[0-9a-f]{32}$"},
            "state": {
                "type": "string",
                "enum": ["implementing", "gate_passed"],
            },
            "passed": {"type": "boolean"},
            "checks": CHECKS_SCHEMA,
        },
        "required": ["flow_id", "state", "passed", "checks"],
        "additionalProperties": False,
    }
)
LANDING_REQUEST_OUTPUT = response_schema(
    {
        "type": "object",
        "properties": {
            "flow_id": {"type": "string", "pattern": "^[0-9a-f]{32}$"},
            "state": {"const": "waiting_owner"},
            "direct_git_enforcement": {"const": False},
        },
        "required": ["flow_id", "state", "direct_git_enforcement"],
        "additionalProperties": False,
    }
)


@mcp.resource(
    "onlyiflow://contract/concise",
    name="onlyiflow-concise-contract",
    title="OnlyiFlow concise workflow contract",
    description="Static, bounded guidance for the OnlyiFlow workflow state machine.",
    mime_type="text/markdown",
)
def concise_contract() -> str:
    return CONCISE_CONTRACT


@mcp.tool(
    name="project_status",
    description="Return OnlyiFlow project state without creating files.",
    output_schema=PROJECT_STATUS_OUTPUT,
    annotations=READ_ONLY,
)
def project_status(project_root: ProjectRoot) -> ToolResult:
    return tool_result(runtime.project_status(project_root))


@mcp.tool(
    name="project_init",
    description="Initialize the project-local OnlyiFlow state boundary.",
    output_schema=PROJECT_INIT_OUTPUT,
    annotations=IDEMPOTENT_MUTATION,
)
def project_init(project_root: ProjectRoot) -> ToolResult:
    return tool_result(runtime.project_init(project_root))


@mcp.tool(
    name="gate_configure",
    description="Replace the deterministic Gate checks before a flow starts.",
    output_schema=GATE_CONFIGURE_OUTPUT,
    annotations=IDEMPOTENT_MUTATION,
)
def gate_configure(project_root: ProjectRoot, checks: GateChecks) -> ToolResult:
    return tool_result(runtime.gate_configure(project_root, checks))


@mcp.tool(
    name="flow_start",
    description="Create one quick, standard, or deep OnlyiFlow flow.",
    output_schema=FLOW_START_OUTPUT,
    annotations=MUTATION,
)
def flow_start(
    project_root: ProjectRoot,
    risk: Risk,
    title: Title,
    mode: FlowMode = "direct",
) -> ToolResult:
    return tool_result(runtime.flow_start(project_root, risk, title, mode))


@mcp.tool(
    name="spec_submit",
    description="Store the compact spec for a draft standard or deep flow.",
    output_schema=SPEC_SUBMIT_OUTPUT,
    annotations=MUTATION,
)
def spec_submit(
    project_root: ProjectRoot,
    flow_id: FlowId,
    goal: SpecText,
    acceptance: SpecText,
    boundaries: SpecText,
    expected_files: ExpectedFiles,
) -> ToolResult:
    return tool_result(
        runtime.spec_submit(
            project_root,
            flow_id,
            goal,
            acceptance,
            boundaries,
            expected_files,
        )
    )


@mcp.tool(
    name="wave_plan_set",
    description="Record one complete owner-confirmed Wave plan or revision.",
    output_schema=WAVE_PLAN_SET_OUTPUT,
    annotations=IDEMPOTENT_MUTATION,
)
def wave_plan_set(
    project_root: ProjectRoot,
    flow_id: FlowId,
    expected_revision: ExpectedRevision,
    packages: Packages,
) -> ToolResult:
    return tool_result(
        runtime.wave_plan_set(
            project_root,
            flow_id,
            expected_revision,
            packages,
        )
    )


@mcp.tool(
    name="flow_claim",
    description="Move a ready standard or deep flow into implementation.",
    output_schema=FLOW_CLAIM_OUTPUT,
    annotations=MUTATION,
)
def flow_claim(project_root: ProjectRoot, flow_id: FlowId) -> ToolResult:
    return tool_result(runtime.flow_claim(project_root, flow_id))


@mcp.tool(
    name="work_package_status",
    description="Return one current Wave work package without host execution.",
    output_schema=WORK_PACKAGE_STATUS_OUTPUT,
    annotations=READ_ONLY,
)
def work_package_status(
    project_root: ProjectRoot,
    flow_id: FlowId,
    package_id: PackageId,
) -> ToolResult:
    return tool_result(runtime.work_package_status(project_root, flow_id, package_id))


@mcp.tool(
    name="work_package_record",
    description="Record one host-completed work package state transition.",
    output_schema=WORK_PACKAGE_RECORD_OUTPUT,
    annotations=MUTATION,
)
def work_package_record(
    project_root: ProjectRoot,
    flow_id: FlowId,
    package_id: PackageId,
    action: PackageAction,
    base_commit: Commit | None = None,
    head_commit: Commit | None = None,
    changed_files: ChangedFiles | None = None,
    checks: PackageChecks | None = None,
    known_limits: KnownLimits | None = None,
    reason_code: ReasonCode | None = None,
    retryable: bool | None = None,
) -> ToolResult:
    return tool_result(
        runtime.work_package_record(
            project_root=project_root,
            flow_id=flow_id,
            package_id=package_id,
            action=action,
            base_commit=base_commit,
            head_commit=head_commit,
            changed_files=changed_files,
            checks=checks,
            known_limits=known_limits,
            reason_code=reason_code,
            retryable=retryable,
        )
    )


@mcp.tool(
    name="gate_run",
    description="Run configured deterministic checks and persist compact evidence.",
    output_schema=GATE_RUN_OUTPUT,
    annotations=MUTATION,
)
def gate_run(project_root: ProjectRoot, flow_id: FlowId) -> ToolResult:
    return tool_result(runtime.gate_run(project_root, flow_id))


@mcp.tool(
    name="landing_request",
    description="Record that a gate-passed flow is waiting for owner-controlled landing.",
    output_schema=LANDING_REQUEST_OUTPUT,
    annotations=MUTATION,
)
def landing_request(project_root: ProjectRoot, flow_id: FlowId) -> ToolResult:
    return tool_result(runtime.landing_request(project_root, flow_id))


def tool_result(payload: dict) -> ToolResult:
    text = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return ToolResult(
        content=[TextContent(type="text", text=text)],
        structured_content=payload,
        is_error=not payload["ok"],
    )
