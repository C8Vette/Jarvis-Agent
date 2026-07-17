from __future__ import annotations

import re
from typing import Any

from core.memory import load_projects, next_project_id, now_iso, save_projects
from skills.tasks import parse_due_text

ACTIVE_STATUSES = {"active", "blocked", "on hold"}
KNOWN_STATUSES = {
    "active": "active",
    "started": "active",
    "in progress": "active",
    "on hold": "on hold",
    "hold": "on hold",
    "paused": "on hold",
    "blocked": "blocked",
    "done": "done",
    "complete": "done",
    "completed": "done",
    "finished": "done",
}


def add_project(description: str) -> str:
    name, due = parse_due_text(description)
    name = _clean_text(name)
    if not name:
        return "I need a project name to add."

    projects = load_projects()
    existing = _find_project(projects, name)
    if existing:
        return f"Project already exists: {existing.get('name')}."

    project: dict[str, Any] = {
        "id": next_project_id(projects),
        "name": name,
        "status": "active",
        "priority": "normal",
        "next_action": "",
        "notes": [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    if due:
        project["due"] = due

    projects.append(project)
    save_projects(projects)
    due_text = f" due {due}" if due else ""
    return f"Added project {project['id']}: {name}{due_text}."


def list_projects(_: str = "") -> str:
    projects = [project for project in load_projects() if project.get("status") != "done"]
    if not projects:
        return "You have no active projects."

    parts = []
    for project in projects[:10]:
        due = f", due {project.get('due')}" if project.get("due") else ""
        next_action = (
            f", next: {project.get('next_action')}"
            if project.get("next_action")
            else ""
        )
        parts.append(
            f"{project.get('id')}: {project.get('name')} "
            f"({project.get('status', 'active')}{due}{next_action})"
        )
    extra = len(projects) - 10
    if extra > 0:
        parts.append(f"{extra} more")
    return "Projects: " + "; ".join(parts) + "."


def set_project_status(target: str) -> str:
    name, status = _parse_status_target(target)
    if not name or not status:
        return "Tell me the project and status, like: set project Jarvis status to active."

    projects = load_projects()
    project = _find_project(projects, name)
    if not project:
        return f"I could not find a project matching: {name}"

    project["status"] = status
    project["updated_at"] = now_iso()
    save_projects(projects)
    return f"Set project {project.get('name')} to {status}."


def set_project_next_action(target: str) -> str:
    name, next_action = _parse_next_action_target(target)
    if not name or not next_action:
        return "Tell me the project and next action, like: set next action for Jarvis to build the tray app."

    projects = load_projects()
    project = _find_project(projects, name)
    if not project:
        return f"I could not find a project matching: {name}"

    project["next_action"] = _clean_text(next_action)
    project["updated_at"] = now_iso()
    save_projects(projects)
    return f"Next action for {project.get('name')}: {project.get('next_action')}."


def active_projects() -> list[dict[str, Any]]:
    return [
        project
        for project in load_projects()
        if project.get("status", "active") in ACTIVE_STATUSES
    ]


def recommended_project_focus() -> str:
    projects = active_projects()
    for project in projects:
        next_action = project.get("next_action")
        if next_action:
            return f"{project.get('name')}: {next_action}"
    if projects:
        return f"{projects[0].get('name')}: choose the next concrete action"
    return ""


def _clean_text(text: str) -> str:
    return text.strip().rstrip(".!?").strip()


def _find_project(projects: list[dict[str, Any]], query: str) -> dict[str, Any] | None:
    normalized = query.strip().lower()
    if not normalized:
        return None

    for project in projects:
        if str(project.get("id", "")) == normalized:
            return project

    exact = [
        project
        for project in projects
        if str(project.get("name", "")).lower() == normalized
    ]
    if exact:
        return exact[0]

    partial = [
        project
        for project in projects
        if normalized in str(project.get("name", "")).lower()
    ]
    return partial[0] if partial else None


def _parse_status_target(target: str) -> tuple[str, str]:
    cleaned = _clean_text(target)
    patterns = [
        r"^(?P<name>.+?)\s+(?:status\s+)?(?:to|as)\s+(?P<status>.+)$",
        r"^(?P<name>.+?)\s+is\s+(?P<status>.+)$",
    ]
    for pattern in patterns:
        match = re.match(pattern, cleaned, flags=re.IGNORECASE)
        if match:
            status = _normalize_status(match.group("status"))
            if status:
                return _clean_text(match.group("name")), status

    words = cleaned.lower().split()
    for size in (2, 1):
        candidate = " ".join(words[-size:])
        status = _normalize_status(candidate)
        if status:
            name = " ".join(cleaned.split()[:-size])
            return _clean_text(name), status
    return cleaned, ""


def _parse_next_action_target(target: str) -> tuple[str, str]:
    cleaned = _clean_text(target)
    patterns = [
        r"^(?P<name>.+?)\s+(?:to|is)\s+(?P<action>.+)$",
        r"^(?P<name>.+?):\s*(?P<action>.+)$",
    ]
    for pattern in patterns:
        match = re.match(pattern, cleaned, flags=re.IGNORECASE)
        if match:
            return _clean_text(match.group("name")), _clean_text(match.group("action"))
    return "", ""


def _normalize_status(status: str) -> str:
    return KNOWN_STATUSES.get(status.strip().lower(), "")
