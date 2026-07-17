from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class PendingRequest:
    action: str
    prompt: str
    data: dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.monotonic)


_PENDING: PendingRequest | None = None
_PENDING_TTL_SECONDS = 300


def pending_summary() -> str:
    if not _PENDING:
        return ""
    return _PENDING.prompt


def clear_pending() -> None:
    global _PENDING
    _PENDING = None


def set_pending(action: str, prompt: str, data: dict[str, str] | None = None) -> str:
    global _PENDING
    _PENDING = PendingRequest(action=action, prompt=prompt, data=data or {})
    return prompt


def handle_pending(
    command: str,
    dispatch: Callable[[str, str, str], str],
) -> str | None:
    global _PENDING
    if not _PENDING:
        return None

    if time.monotonic() - _PENDING.created_at > _PENDING_TTL_SECONDS:
        _PENDING = None
        return None

    text = command.strip()
    normalized = text.lower().strip(" .!?")
    if normalized in {"cancel", "nevermind", "never mind", "stop", "forget it"}:
        _PENDING = None
        return "Okay, I cancelled that."

    pending = _PENDING
    _PENDING = None

    if pending.action == "add_task":
        description = _clean_task_followup(text)
        due = pending.data.get("due", "")
        if due and " due " not in description.lower():
            description = f"{description} due {due}"
        return dispatch("add_task", description, command)

    if pending.action == "set_assistant_mode":
        mode = _clean_mode_followup(text)
        return dispatch("set_assistant_mode", mode, command)

    return None


def _clean_task_followup(text: str) -> str:
    cleaned = text.strip()
    patterns = [
        r"^(?:it is|it's|its)\s+",
        r"^(?:the task is|task is)\s+",
        r"^(?:the description is|description is)\s+",
        r"^(?:call it|called|name it|named|title it|titled)\s+",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, count=1, flags=re.IGNORECASE).strip()
    return cleaned


def _clean_mode_followup(text: str) -> str:
    cleaned = text.strip().lower().strip(" .!?")
    patterns = [
        r"^(?:use|switch to|set|change to|go to)\s+",
        r"^(?:the\s+)?(?:jarvis\s+)?(?:assistant\s+)?mode\s+(?:to\s+)?",
        r"\s+mode$",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, count=1, flags=re.IGNORECASE).strip()
    return cleaned
