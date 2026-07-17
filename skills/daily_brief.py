from __future__ import annotations

from datetime import date, datetime

from core.config import load_user_config
from skills.tasks import overdue_tasks, tasks_due_on, upcoming_tasks, open_tasks
from skills.projects import active_projects, recommended_project_focus
from skills.reminders import open_reminders, reminders_due_on, upcoming_reminders
from skills.gmail import gmail_digest_data


def _format_list(items) -> str:
    clean = [str(item).strip() for item in items or [] if str(item).strip()]
    if not clean:
        return "nothing configured yet"
    return "; ".join(clean)


def _format_tasks(tasks, limit: int = 4) -> str:
    if not tasks:
        return "none"
    parts = []
    for task in tasks[:limit]:
        due = f" due {task.get('due')}" if task.get("due") else ""
        parts.append(f"{task.get('title')}{due}")
    extra = len(tasks) - limit
    if extra > 0:
        parts.append(f"{extra} more")
    return "; ".join(parts)


def _format_projects(projects, limit: int = 4) -> str:
    if not projects:
        return "nothing configured yet"
    parts = []
    for project in projects[:limit]:
        due = f" due {project.get('due')}" if project.get("due") else ""
        next_action = f", next: {project.get('next_action')}" if project.get("next_action") else ""
        parts.append(f"{project.get('name')}{due}{next_action}")
    extra = len(projects) - limit
    if extra > 0:
        parts.append(f"{extra} more")
    return "; ".join(parts)


def _format_email(messages, limit: int = 3) -> str:
    if not messages:
        return "none"
    parts = []
    for message in messages[:limit]:
        sender = message.get("from") or "unknown sender"
        subject = message.get("subject") or "no subject"
        parts.append(f"{sender}: {subject}")
    extra = len(messages) - limit
    if extra > 0:
        parts.append(f"{extra} more")
    return "; ".join(parts)


def _recommended_focus(overdue, due_today, reminders_today, project_focus: str) -> str:
    if overdue:
        task = overdue[0]
        return f"clear overdue task: {task.get('title')}"
    if due_today:
        task = due_today[0]
        return f"finish today's task: {task.get('title')}"
    if reminders_today:
        reminder = reminders_today[0]
        return f"handle reminder: {reminder.get('title')}"
    if project_focus:
        return project_focus
    return "pick one school task before opening distractions"


def daily_brief() -> str:
    user = load_user_config()
    profile = user.get("profile", {})
    routine = user.get("routine", {})
    school = user.get("school", {})
    projects = user.get("projects", [])

    name = profile.get("name", "there")
    today = datetime.now().strftime("%A, %B %d")

    focus_items = routine.get("daily_focus", [])
    morning_checklist = routine.get("morning_checklist", [])
    school_sources = school.get("sources", [])
    courses = school.get("courses", [])
    configured_projects = [
        project for project in projects
        if project.get("name") and project.get("status", "active") == "active"
    ]
    memory_projects = active_projects()
    configured_project_names = [
        {"name": project.get("name"), "status": "active"}
        for project in configured_projects
        if project.get("name")
    ]
    merged_projects = memory_projects + [
        project
        for project in configured_project_names
        if project.get("name") not in {item.get("name") for item in memory_projects}
    ]

    overdue = overdue_tasks()
    due_today = tasks_due_on(date.today())
    upcoming = upcoming_tasks()
    open_count = len(open_tasks())
    project_focus = recommended_project_focus()
    reminders_today = reminders_due_on(date.today())
    reminders_upcoming = upcoming_reminders()
    reminder_count = len(open_reminders())
    gmail = gmail_digest_data()
    gmail_messages = gmail.get("messages", [])

    return (
        f"Good morning, {name}. Today is {today}. "
        f"You have {open_count} open tasks. "
        f"Overdue: {_format_tasks(overdue)}. "
        f"Due today: {_format_tasks(due_today)}. "
        f"Upcoming this week: {_format_tasks(upcoming)}. "
        f"Reminders: {reminder_count} open; today: {_format_tasks(reminders_today)}; upcoming: {_format_tasks(reminders_upcoming)}. "
        f"Important email: {_format_email(gmail_messages)}. "
        f"Recommended focus: {_recommended_focus(overdue, due_today, reminders_today, project_focus)}. "
        f"Morning checklist: {_format_list(morning_checklist)}. "
        f"Focus: {_format_list(focus_items)}. "
        f"School sources: {_format_list(school_sources)}. "
        f"Courses: {_format_list(courses)}. "
        f"Active projects: {_format_projects(merged_projects)}."
    )
