from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from core.memory import load_tasks, next_task_id, now_iso, save_tasks

MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


def parse_due_text(text: str) -> tuple[str, str]:
    """Return (title_without_due_phrase, due_iso_or_empty)."""
    cleaned = text.strip()
    lowered = cleaned.lower()

    relative = {
        "today": date.today(),
        "tomorrow": date.today() + timedelta(days=1),
    }
    for phrase, due_date in relative.items():
        match = re.search(rf"\s+due\s+{phrase}\b", lowered)
        if match:
            title = cleaned[: match.start()].strip()
            return title, due_date.isoformat()

    iso_match = re.search(r"\s+due\s+(\d{4}-\d{2}-\d{2})\b", cleaned, flags=re.IGNORECASE)
    if iso_match:
        title = cleaned[: iso_match.start()].strip()
        return title, iso_match.group(1)

    month_names = "|".join(MONTHS)
    month_match = re.search(
        rf"\s+due(?:\s+on)?\s+({month_names})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?\b",
        cleaned,
        flags=re.IGNORECASE,
    )
    if month_match:
        today = date.today()
        month = MONTHS[month_match.group(1).lower()]
        day = int(month_match.group(2))
        year = int(month_match.group(3) or today.year)
        due_date = date(year, month, day)
        if month_match.group(3) is None and due_date < today:
            due_date = date(year + 1, month, day)
        title = cleaned[: month_match.start()].strip()
        return title, due_date.isoformat()

    return cleaned, ""


def add_task(description: str) -> str:
    title, due = parse_due_text(description)
    title = title.strip().rstrip(".!?").strip()
    if not title:
        return "I need a task description to add."

    tasks = load_tasks()
    task = {
        "id": next_task_id(tasks),
        "title": title,
        "status": "open",
        "source": "manual",
        "created_at": now_iso(),
    }
    if due:
        task["due"] = due

    tasks.append(task)
    save_tasks(tasks)

    due_text = f" due {due}" if due else ""
    return f"Added task {task['id']}: {title}{due_text}."


def open_tasks() -> list[dict]:
    return [task for task in load_tasks() if task.get("status", "open") == "open"]


def list_tasks(_: str = "") -> str:
    tasks = open_tasks()
    if not tasks:
        return "You have no open tasks."

    lines = []
    for task in tasks[:12]:
        due = f", due {task.get('due')}" if task.get("due") else ""
        lines.append(f"{task.get('id')}: {task.get('title')}{due}")
    return "Open tasks: " + "; ".join(lines) + "."


def complete_task(target: str) -> str:
    query = target.strip().lower()
    if not query:
        return "Tell me which task to complete."

    tasks = load_tasks()
    matched = None
    for task in tasks:
        task_id = str(task.get("id", ""))
        title = str(task.get("title", "")).lower()
        if query == task_id or query in title:
            matched = task
            break

    if not matched:
        return f"I could not find an open task matching: {target}"

    matched["status"] = "done"
    matched["completed_at"] = now_iso()
    save_tasks(tasks)
    return f"Completed task {matched.get('id')}: {matched.get('title')}."


def tasks_due_on(target_date: date) -> list[dict]:
    return [
        task
        for task in open_tasks()
        if task.get("due") == target_date.isoformat()
    ]


def overdue_tasks() -> list[dict]:
    today = date.today()
    overdue = []
    for task in open_tasks():
        due = task.get("due")
        if not due:
            continue
        try:
            due_date = datetime.strptime(due, "%Y-%m-%d").date()
        except ValueError:
            continue
        if due_date < today:
            overdue.append(task)
    return overdue


def upcoming_tasks(days: int = 7) -> list[dict]:
    today = date.today()
    end = today + timedelta(days=days)
    upcoming = []
    for task in open_tasks():
        due = task.get("due")
        if not due:
            continue
        try:
            due_date = datetime.strptime(due, "%Y-%m-%d").date()
        except ValueError:
            continue
        if today < due_date <= end:
            upcoming.append(task)
    return upcoming
