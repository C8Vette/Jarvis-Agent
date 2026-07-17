"""Safety policy and filesystem sandbox for Jarvis.

Two responsibilities:

1. Filesystem sandbox - the single source of truth for "is this path inside an
   allowed folder?" Skills that touch the disk import their checks from here.
2. Action policy - enforces config/permissions.yaml. Actions listed under
   `auto_allow` run immediately; actions under `require_confirmation` need an
   explicit yes; anything in neither list is blocked.
"""

from pathlib import Path
from typing import List, Tuple

from rich.prompt import Confirm

from core.actions import AUTO_ALLOW, BLOCKED, REQUIRE_CONFIRMATION, get_action_definition
from core.config import load_device_config, load_permissions


# ---------------------------------------------------------------------------
# Filesystem sandbox
# ---------------------------------------------------------------------------
def get_allowed_roots() -> List[Path]:
    config = load_device_config()
    return [Path(folder) for folder in config.get("allowed_folders", [])]


def is_allowed_path(path) -> bool:
    """True if `path` resolves to a location inside an allowed folder."""
    try:
        resolved = Path(path).resolve()
    except Exception:
        return False

    for root in get_allowed_roots():
        try:
            if root.exists() and resolved.is_relative_to(root.resolve()):
                return True
        except Exception:
            continue
    return False


def assert_allowed_path(path) -> None:
    """Raise PermissionError if `path` is outside the sandbox. For use by any
    future skill that writes/moves/deletes before it touches the disk."""
    if not is_allowed_path(path):
        raise PermissionError(f"Path is outside Jarvis's allowed folders: {path}")


# ---------------------------------------------------------------------------
# Action policy  (config/permissions.yaml)
# ---------------------------------------------------------------------------
def classify_action(action: str) -> str:
    """Return AUTO_ALLOW, REQUIRE_CONFIRMATION, or BLOCKED for an action name."""
    policy = load_permissions()
    if action in policy.get("auto_allow", []):
        return AUTO_ALLOW
    if action in policy.get("require_confirmation", []):
        return REQUIRE_CONFIRMATION
    if action in policy.get("blocked", []):
        return BLOCKED

    definition = get_action_definition(action)
    if definition:
        return definition.default_policy

    return BLOCKED


def is_auto_allowed(action: str) -> bool:
    return classify_action(action) == AUTO_ALLOW


def requires_confirmation(action: str) -> bool:
    return classify_action(action) == REQUIRE_CONFIRMATION


def _ask_confirm(action: str, detail: str = "") -> bool:
    message = f"[yellow]Jarvis wants to run[/yellow] [bold]{action}[/bold]"
    if detail:
        message += f" [yellow]on[/yellow] [bold]{detail}[/bold]"
    message += ". Allow?"
    try:
        return Confirm.ask(message, default=False)
    except (EOFError, KeyboardInterrupt):
        return False


# Module-level hook so a future voice UI (or tests) can replace how the user is
# asked to confirm, without touching the policy logic.
confirmer = _ask_confirm


def check_action(action: str, detail: str = "") -> Tuple[bool, str]:
    """Decide whether an action may run, prompting if the policy requires it.

    Returns (allowed, message). When not allowed, `message` explains why and is
    safe to return straight to the user.
    """
    status = classify_action(action)

    if status == AUTO_ALLOW:
        return True, ""

    if status == REQUIRE_CONFIRMATION:
        if confirmer(action, detail):
            return True, ""
        return False, f"Cancelled: '{action}' was not confirmed."

    return False, (
        f"Blocked: '{action}' is not enabled. "
        "Add it to config/permissions.yaml or the action registry to enable it."
    )
