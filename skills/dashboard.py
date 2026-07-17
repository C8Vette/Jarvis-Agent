from __future__ import annotations

from datetime import date, datetime
from typing import Any

from core.config import load_user_config
from skills.daily_brief import daily_brief
from skills.projects import active_projects, recommended_project_focus
from skills.reminders import open_reminders, reminders_due_on, upcoming_reminders
from skills.tasks import open_tasks, overdue_tasks, tasks_due_on, upcoming_tasks
from skills.gmail import gmail_digest_data, gmail_status


def dashboard_state() -> dict[str, Any]:
    user = load_user_config()
    school = user.get("school", {})
    routine = user.get("routine", {})

    overdue = overdue_tasks()
    due_today = tasks_due_on(date.today())
    upcoming = upcoming_tasks()
    projects = active_projects()
    reminders = open_reminders()
    reminders_today = reminders_due_on(date.today())
    reminders_upcoming = upcoming_reminders()
    gmail = gmail_digest_data()
    focus = _recommended_focus(overdue, due_today, reminders_today, recommended_project_focus())

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "today": date.today().isoformat(),
        "brief": daily_brief(),
        "recommended_focus": focus,
        "counts": {
            "open_tasks": len(open_tasks()),
            "overdue_tasks": len(overdue),
            "due_today": len(due_today),
            "active_projects": len(projects),
            "open_reminders": len(reminders),
            "gmail_messages": len(gmail.get("messages", [])),
        },
        "tasks": {
            "open": open_tasks(),
            "overdue": overdue,
            "due_today": due_today,
            "upcoming": upcoming,
        },
        "projects": {
            "active": projects,
            "focus": recommended_project_focus(),
        },
        "school": {
            "lms": school.get("lms", ""),
            "moodle_url": school.get("moodle_url", ""),
            "sources": school.get("sources", []),
            "courses": school.get("courses", []),
        },
        "routine": {
            "morning_checklist": routine.get("morning_checklist", []),
            "daily_focus": routine.get("daily_focus", []),
        },
        "reminders": {
            "open": reminders,
            "due_today": reminders_today,
            "upcoming": reminders_upcoming,
        },
        "gmail": {
            "status": gmail_status(),
            "configured": gmail.get("configured", False),
            "message": gmail.get("message", ""),
            "messages": gmail.get("messages", []),
        },
    }


def _recommended_focus(
    overdue: list[dict[str, Any]],
    due_today: list[dict[str, Any]],
    reminders_today: list[dict[str, Any]],
    project_focus: str,
) -> str:
    if overdue:
        return f"Clear overdue task: {overdue[0].get('title')}"
    if due_today:
        return f"Finish today's task: {due_today[0].get('title')}"
    if reminders_today:
        return f"Handle reminder: {reminders_today[0].get('title')}"
    if project_focus:
        return project_focus
    return "Pick one school task before opening distractions"
