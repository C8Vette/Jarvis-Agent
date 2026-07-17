from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.config import ROOT

AUDIT_LOG = ROOT / "data" / "audit.log"


def log_action(
    action: str,
    target: str = "",
    status: str = "",
    message: str = "",
    command: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Append one JSON line for each action decision/execution."""
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "target": target,
        "status": status,
        "message": message,
        "command": command,
        "metadata": metadata or {},
    }

    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=True) + "\n")
