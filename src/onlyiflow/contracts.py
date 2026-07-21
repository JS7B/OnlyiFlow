"""定义稳定的成功、失败与领域错误载荷契约。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


Payload = dict[str, Any]
NextAction = dict[str, str]


@dataclass
class DomainError(Exception):
    code: str
    message: str
    retryable: bool
    next_action: NextAction | None = None


def success(data: Payload, next_action: NextAction | None = None) -> Payload:
    payload: Payload = {"ok": True, "data": data}
    if next_action is not None:
        payload["next_action"] = next_action
    return payload


def failure(error: DomainError) -> Payload:
    payload: Payload = {
        "ok": False,
        "error": {
            "code": error.code,
            "message": error.message,
            "retryable": error.retryable,
        },
    }
    if error.next_action is not None:
        payload["next_action"] = error.next_action
    return payload
