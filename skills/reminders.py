from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from core.memory import load_reminders, next_reminder_id, now_iso, save_reminders
from skills.tasks import parse_due_text


def add_reminder(description: str) -> str:
    title, due = parse_due_text(description)
    title = title.strip().rstrip(".!?").strip()
    if not title:
        return "I need a reminder description to add."

    reminders = load_reminders()
    reminder: dict[str, Any] = {
        "id": next_reminder_id(reminders),
        "title": title,
        "status": "open",
        "created_at": now_iso(),
    }
    if due:
        reminder["due"] = due

    reminders.append(reminder)
    save_reminders(reminders)
    due_text = f" due {due}" if due else ""
    return f"Added reminder {reminder['id']}: {title}{due_text}."


def open_reminders() -> list[dict[str, Any]]:
    return [
        reminder
        for reminder in load_reminders()
        if reminder.get("status", "open") == "open"
    ]


def list_reminders(_: str = "") -> str:
    reminders = open_reminders()
    if not reminders:
        return "You have no open reminders."

    parts = []
    for reminder in reminders[:12]:
        due = f", due {reminder.get('due')}" if reminder.get("due") else ""
        parts.append(f"{reminder.get('id')}: {reminder.get('title')}{due}")
    return "Reminders: " + "; ".join(parts) + "."


def complete_reminder(target: str) -> str:
    query = target.strip().lower()
    if not query:
        return "Tell me which reminder to complete."

    reminders = load_reminders()
    matched = None
    for reminder in reminders:
        reminder_id = str(reminder.get("id", ""))
        title = str(reminder.get("title", "")).lower()
        if query == reminder_id or query in title:
            matched = reminder
            break

    if not matched:
        return f"I could not find an open reminder matching: {target}"

    matched["status"] = "done"
    matched["completed_at"] = now_iso()
    save_reminders(reminders)
    return f"Completed reminder {matched.get('id')}: {matched.get('title')}."


def reminders_due_on(target_date: date) -> list[dict[str, Any]]:
    return [
        reminder
        for reminder in open_reminders()
        if reminder.get("due") == target_date.isoformat()
    ]


def upcoming_reminders(days: int = 7) -> list[dict[str, Any]]:
    today = date.today()
    end = today + timedelta(days=days)
    upcoming = []
    for reminder in open_reminders():
        due = reminder.get("due")
        if not due:
            continue
        try:
            due_date = datetime.strptime(due, "%Y-%m-%d").date()
        except ValueError:
            continue
        if today <= due_date <= end:
            upcoming.append(reminder)
    return upcoming
