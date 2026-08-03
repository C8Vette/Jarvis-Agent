from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from core.config import ROOT

TASKS_PATH = ROOT / "data" / "tasks.yaml"
PROJECTS_PATH = ROOT / "data" / "projects.yaml"
REMINDERS_PATH = ROOT / "data" / "reminders.yaml"
OPERATOR_JOBS_PATH = ROOT / "data" / "operator_jobs.yaml"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_yaml_file(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return default or {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or (default or {})


def save_yaml_file(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=False)


def load_tasks() -> list[dict[str, Any]]:
    data = load_yaml_file(TASKS_PATH, {"tasks": []})
    return list(data.get("tasks", []))


def save_tasks(tasks: list[dict[str, Any]]) -> None:
    save_yaml_file(TASKS_PATH, {"tasks": tasks})


def next_task_id(tasks: list[dict[str, Any]]) -> int:
    ids = [int(task.get("id", 0)) for task in tasks if str(task.get("id", "")).isdigit()]
    return max(ids, default=0) + 1


def load_projects() -> list[dict[str, Any]]:
    data = load_yaml_file(PROJECTS_PATH, {"projects": []})
    return list(data.get("projects", []))


def save_projects(projects: list[dict[str, Any]]) -> None:
    save_yaml_file(PROJECTS_PATH, {"projects": projects})


def next_project_id(projects: list[dict[str, Any]]) -> int:
    ids = [
        int(project.get("id", 0))
        for project in projects
        if str(project.get("id", "")).isdigit()
    ]
    return max(ids, default=0) + 1


def load_reminders() -> list[dict[str, Any]]:
    data = load_yaml_file(REMINDERS_PATH, {"reminders": []})
    return list(data.get("reminders", []))


def save_reminders(reminders: list[dict[str, Any]]) -> None:
    save_yaml_file(REMINDERS_PATH, {"reminders": reminders})


def next_reminder_id(reminders: list[dict[str, Any]]) -> int:
    ids = [
        int(reminder.get("id", 0))
        for reminder in reminders
        if str(reminder.get("id", "")).isdigit()
    ]
    return max(ids, default=0) + 1


def load_operator_jobs() -> list[dict[str, Any]]:
    data = load_yaml_file(OPERATOR_JOBS_PATH, {"operator_jobs": []})
    return list(data.get("operator_jobs", []))


def save_operator_jobs(jobs: list[dict[str, Any]]) -> None:
    save_yaml_file(OPERATOR_JOBS_PATH, {"operator_jobs": jobs})


def next_operator_job_id(jobs: list[dict[str, Any]]) -> int:
    ids = [
        int(job.get("id", 0))
        for job in jobs
        if str(job.get("id", "")).isdigit()
    ]
    return max(ids, default=0) + 1