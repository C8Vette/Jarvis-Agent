from __future__ import annotations

from typing import Any

from core.memory import (
    load_operator_jobs,
    next_operator_job_id,
    now_iso,
    save_operator_jobs,
)

ACTIVE_STATUSES = {"queued", "planning", "waiting_for_approval", "running", "blocked"}


def create_operator_job(objective: str) -> str:
    objective = _clean(objective)
    if not objective:
        return "Tell me what supervised job you want Jarvis to queue."

    jobs = load_operator_jobs()
    job = {
        "id": next_operator_job_id(jobs),
        "objective": objective,
        "status": "queued",
        "safety_level": "manual_review",
        "check_in_policy": "before any external action or terminal approval",
        "current_step": "queued for supervisor planning",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "events": [
            {
                "timestamp": now_iso(),
                "type": "created",
                "message": "Job queued. No external actions have been run.",
            }
        ],
    }
    jobs.append(job)
    save_operator_jobs(jobs)
    return (
        f"Queued supervised operator job {job['id']}: {objective}. "
        "I will not run tools, terminals, Claude, ChatGPT, or Codex for this job until the operator executor is enabled and approval rules are in place."
    )


def list_operator_jobs(_: str = "") -> str:
    jobs = [job for job in load_operator_jobs() if job.get("status") in ACTIVE_STATUSES]
    if not jobs:
        return "There are no active supervised operator jobs."

    parts = []
    for job in jobs[:10]:
        parts.append(
            f"{job.get('id')}: {job.get('objective')} "
            f"({job.get('status')}; {job.get('current_step', 'queued')})"
        )
    extra = len(jobs) - 10
    if extra > 0:
        parts.append(f"{extra} more")
    return "Operator jobs: " + "; ".join(parts) + "."


def operator_status(target: str = "") -> str:
    jobs = load_operator_jobs()
    if not jobs:
        return "There are no supervised operator jobs yet."

    job = _find_job(jobs, target) if target.strip() else _latest_active(jobs) or jobs[-1]
    if not job:
        return f"I could not find an operator job matching: {target}"

    return (
        f"Operator job {job.get('id')}: {job.get('objective')}. "
        f"Status: {job.get('status')}. Current step: {job.get('current_step', 'queued')}. "
        f"Safety: {job.get('safety_level', 'manual_review')}. "
        f"Check-in: {job.get('check_in_policy', 'before risky actions')}."
    )


def cancel_operator_job(target: str) -> str:
    query = _clean(target).lower()
    if not query:
        return "Tell me which operator job to cancel."

    jobs = load_operator_jobs()
    job = _find_job(jobs, query)
    if not job:
        return f"I could not find an operator job matching: {target}"

    if job.get("status") == "canceled":
        return f"Operator job {job.get('id')} is already canceled."

    job["status"] = "canceled"
    job["current_step"] = "canceled by user"
    job["updated_at"] = now_iso()
    job.setdefault("events", []).append(
        {
            "timestamp": now_iso(),
            "type": "canceled",
            "message": "Canceled by user request.",
        }
    )
    save_operator_jobs(jobs)
    return f"Canceled operator job {job.get('id')}: {job.get('objective')}."


def _clean(text: str) -> str:
    return text.strip().rstrip(".!?").strip()


def _find_job(jobs: list[dict[str, Any]], query: str) -> dict[str, Any] | None:
    normalized = query.strip().lower()
    if not normalized:
        return None

    for job in jobs:
        if str(job.get("id", "")) == normalized:
            return job

    for job in jobs:
        if normalized in str(job.get("objective", "")).lower():
            return job

    return None


def _latest_active(jobs: list[dict[str, Any]]) -> dict[str, Any] | None:
    for job in reversed(jobs):
        if job.get("status") in ACTIVE_STATUSES:
            return job
    return None