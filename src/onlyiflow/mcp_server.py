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
    "flow_start",
    "spec_submit",
    "flow_claim",
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
                },
                "required": ["managed", "active_flow", "latest_gate"],
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
FLOW_CLAIM_OUTPUT = FLOW_START_OUTPUT
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
    name="flow_start",
    description="Create one quick, standard, or deep OnlyiFlow flow.",
    output_schema=FLOW_START_OUTPUT,
    annotations=MUTATION,
)
def flow_start(project_root: ProjectRoot, risk: Risk, title: Title) -> ToolResult:
    return tool_result(runtime.flow_start(project_root, risk, title))


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
    name="flow_claim",
    description="Move a ready standard or deep flow into implementation.",
    output_schema=FLOW_CLAIM_OUTPUT,
    annotations=MUTATION,
)
def flow_claim(project_root: ProjectRoot, flow_id: FlowId) -> ToolResult:
    return tool_result(runtime.flow_claim(project_root, flow_id))


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
