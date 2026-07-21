"""定义 Flow 标识符、风险校验与核心领域值检查。"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import uuid4

from .contracts import DomainError


RISKS = {"quick", "standard", "deep"}
FLOW_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
MAX_TITLE_LENGTH = 200
MAX_SPEC_TEXT_LENGTH = 4000


def new_flow_id() -> str:
    return uuid4().hex


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def validate_risk(risk: str) -> str:
    if not isinstance(risk, str) or risk not in RISKS:
        raise DomainError(
            code="risk_invalid",
            message="Risk must be quick, standard, or deep.",
            retryable=True,
        )
    return risk


def validate_flow_id(flow_id: str) -> str:
    if not isinstance(flow_id, str) or not FLOW_ID_PATTERN.fullmatch(flow_id):
        raise DomainError(
            code="flow_id_invalid",
            message="Flow ID is invalid.",
            retryable=True,
        )
    return flow_id


def validate_text(
    value: str,
    *,
    field: str,
    maximum: int,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DomainError(
            code=f"{field}_required",
            message=f"{field.replace('_', ' ').capitalize()} is required.",
            retryable=True,
        )
    normalized = value.strip()
    if len(normalized) > maximum:
        raise DomainError(
            code=f"{field}_too_long",
            message=f"{field.replace('_', ' ').capitalize()} is too long.",
            retryable=True,
        )
    return normalized
