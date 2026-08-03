import re

from core.conversation import handle_pending, set_pending
from core.config import load_device_config
from core.llm_router import llm_route
from core.audit import log_action
from core.safety import check_action
from skills.browser import open_website, search_web, search_youtube
from skills.system import open_app
from skills.files import search_files
from skills.file_actions import open_folder, open_best_file_match
from skills.daily_brief import daily_brief
from skills.tasks import add_task, complete_task, list_tasks, parse_due_text
from skills.settings import (
    assistant_mode_status,
    set_assistant_mode,
    set_elevenlabs_voice,
    set_tts_enabled,
    set_tts_provider,
    tts_status,
)
from skills.projects import add_project, list_projects, set_project_next_action, set_project_status
from skills.reminders import add_reminder, complete_reminder, list_reminders
from skills.gmail import gmail_connect, gmail_digest, gmail_status
from skills.operator import cancel_operator_job, create_operator_job, list_operator_jobs, operator_status

# Exact phrases that map straight to a known folder.
_FOLDER_PHRASES = {
    "open downloads": "downloads",
    "open my downloads": "downloads",
    "open documents": "documents",
    "open my documents": "documents",
    "open desktop": "desktop",
    "open my desktop": "desktop",
}

_OPEN_VERBS = r"(?<!\w)(?:open|launch|show|pull|go|bring|start|run)(?!\w)"
_MODE_NAMES = r"(?:command|conversation|push\s+to\s+talk|push-to-talk|push_to_talk|assist|cheap|realtime|real\s+time)"


def _normalize(command: str) -> str:
    return re.sub(r"\s+", " ", command.strip().lower())


def _match_config_key(text: str, keys) -> str | None:
    """Return the longest config key that appears as a whole word in text."""
    best = None
    for key in keys:
        k = key.lower()
        if re.search(rf"(?<!\w){re.escape(k)}(?!\w)", text):
            if best is None or len(k) > len(best):
                best = k
    return best


def _strip_prefix(command: str, prefix: str) -> str:
    return command.strip()[len(prefix):].strip()


def _start_pending_task(command: str) -> str:
    _, due = parse_due_text(command)
    data = {"due": due} if due else {}
    if due:
        prompt = f"Sure. What should I call that task? I have it marked due {due}."
    else:
        prompt = "Sure. What task should I add?"
    return set_pending("add_task", prompt, data)


def _start_pending_mode() -> str:
    return set_pending(
        "set_assistant_mode",
        "Which mode should I use: command, conversation, push-to-talk, or assist?",
    )


def _route_generic_task_request(text: str, command: str) -> str | None:
    detail_match = re.search(
        r"\badd(?:\s+another|\s+a|\s+one)?\s+task\s+(?:to|called|named|for)\s+(.+)$",
        command,
        flags=re.IGNORECASE,
    )
    if detail_match:
        return _dispatch_action("add_task", detail_match.group(1).strip(), command)

    if re.search(r"\b(?:add|create|track|remember)\b.*\b(?:task|todo|to do)\b", text):
        return _start_pending_task(command)

    return None


def _clean_mode_target(value: str) -> str:
    target = value.strip().lower().strip(" .!?")
    target = re.sub(r"^(?:the\s+)?(?:jarvis\s+)?(?:assistant\s+)?", "", target).strip()
    target = re.sub(r"\s+mode$", "", target).strip()
    return target


def _route_mode_request(text: str, command: str) -> str | None:
    clean_text = text.strip().strip(" .!?")

    if clean_text in {
        "switch mode",
        "change mode",
        "set mode",
        "change assistant mode",
        "switch assistant mode",
        "set assistant mode",
    }:
        return _start_pending_mode()

    mode_target_match = re.match(
        rf"^(?:switch|set|change|use|go)\s+(?:to\s+)?(?:jarvis\s+)?(?:assistant\s+)?(?:mode\s+)?(?:to\s+)?(?P<mode>{_MODE_NAMES})(?:\s+mode)?[.!?]?$",
        command,
        flags=re.IGNORECASE,
    )
    if mode_target_match:
        return _dispatch_action(
            "set_assistant_mode",
            _clean_mode_target(mode_target_match.group("mode")),
            command,
        )

    mode_first_match = re.match(
        rf"^(?P<mode>{_MODE_NAMES})\s+mode[.!?]?$",
        command,
        flags=re.IGNORECASE,
    )
    if mode_first_match:
        return _dispatch_action(
            "set_assistant_mode",
            _clean_mode_target(mode_first_match.group("mode")),
            command,
        )

    mode_to_match = re.match(
        rf"^(?:set|switch|change)\s+(?:jarvis\s+)?(?:assistant\s+)?mode\s+to\s+(?P<mode>{_MODE_NAMES})[.!?]?$",
        command,
        flags=re.IGNORECASE,
    )
    if mode_to_match:
        return _dispatch_action(
            "set_assistant_mode",
            _clean_mode_target(mode_to_match.group("mode")),
            command,
        )

    return None


def _execute_action(action: str, target: str, command: str, handler) -> str:
    allowed, message = check_action(action, target)
    if not allowed:
        log_action(action, target, "blocked", message, command)
        return message

    log_action(action, target, "started", "", command)
    try:
        result = handler(target)
    except Exception as exc:
        error = f"Failed to run '{action}': {exc}"
        log_action(action, target, "failed", error, command)
        return error

    log_action(action, target, "succeeded", result, command)
    return result


def _dispatch_action(action: str, target: str, command: str) -> str:
    handlers = {
        "open_website": open_website,
        "open_app": open_app,
        "search_files": search_files,
        "open_folder": open_folder,
        "open_file": open_best_file_match,
        "daily_brief": lambda _: daily_brief(),
        "add_task": add_task,
        "list_tasks": list_tasks,
        "complete_task": complete_task,
        "add_reminder": add_reminder,
        "list_reminders": list_reminders,
        "complete_reminder": complete_reminder,
        "gmail_connect": gmail_connect,
        "gmail_digest": gmail_digest,
        "gmail_status": gmail_status,
        "add_project": add_project,
        "list_projects": list_projects,
        "set_project_status": set_project_status,
        "set_project_next_action": set_project_next_action,
        "set_tts_provider": set_tts_provider,
        "set_tts_enabled": set_tts_enabled,
        "tts_status": tts_status,
        "set_elevenlabs_voice": set_elevenlabs_voice,
        "set_assistant_mode": set_assistant_mode,
        "assistant_mode_status": assistant_mode_status,
        "search_web": search_web,
        "search_youtube": search_youtube,
        "create_operator_job": create_operator_job,
        "list_operator_jobs": list_operator_jobs,
        "operator_status": operator_status,
        "cancel_operator_job": cancel_operator_job,
    }

    handler = handlers.get(action)
    if not handler:
        log_action(action, target, "unimplemented", "", command)
        return f"'{action}' is permitted but not implemented yet."

    return _execute_action(action, target, command, handler)


def _local_route(text: str, command: str):
    """Deterministic, no-API routing. All branches here are auto_allow opens.
    Returns a result string, or None to fall through to the LLM router."""
    # 1) Known folders
    if text in _FOLDER_PHRASES:
        return _dispatch_action("open_folder", _FOLDER_PHRASES[text], command)

    # 1b) Personal operating loop
    if text in {
        "brief",
        "be brief",
        "daily",
        "daily brief",
        "morning brief",
        "give me a brief",
        "give me my brief",
        "what should i focus on today",
        "what should i focus on today?",
        "what do i need to do today",
        "what do i need to do today?",
        "what schoolwork do i have",
        "what schoolwork do i have?",
    }:
        return _dispatch_action("daily_brief", "", command)

    if text in {
        "tasks",
        "my tasks",
        "open tasks",
        "what are my tasks",
        "what are my tasks?",
        "what do i have to do",
        "what do i have to do?",
    }:
        return _dispatch_action("list_tasks", "", command)

    for prefix in ("add task ", "create task ", "remember task ", "remind me to "):
        if text.startswith(prefix):
            return _dispatch_action("add_task", _strip_prefix(command, prefix), command)

    generic_task = _route_generic_task_request(text, command)
    if generic_task is not None:
        return generic_task

    for prefix in ("complete task ", "finish task ", "mark task "):
        if text.startswith(prefix):
            target = _strip_prefix(command, prefix).removesuffix(" complete").strip()
            return _dispatch_action("complete_task", target, command)

    if text in {
        "reminders",
        "my reminders",
        "what are my reminders",
        "what are my reminders?",
        "list reminders",
        "list my reminders",
    }:
        return _dispatch_action("list_reminders", "", command)

    for prefix in ("add reminder ", "create reminder ", "remember to "):
        if text.startswith(prefix):
            return _dispatch_action("add_reminder", _strip_prefix(command, prefix), command)

    for prefix in ("complete reminder ", "finish reminder ", "mark reminder "):
        if text.startswith(prefix):
            target = _strip_prefix(command, prefix).removesuffix(" complete").strip()
            return _dispatch_action("complete_reminder", target, command)

    if text in {
        "gmail status",
        "email status",
        "check gmail status",
        "check email status",
    }:
        return _dispatch_action("gmail_status", "", command)

    if text in {
        "connect gmail",
        "connect my gmail",
        "authorize gmail",
        "authorize my gmail",
    }:
        return _dispatch_action("gmail_connect", "", command)

    if text in {
        "check gmail",
        "check my gmail",
        "check email",
        "check my email",
        "gmail digest",
        "email digest",
        "important email",
        "important emails",
        "read important email",
        "read important emails",
    }:
        return _dispatch_action("gmail_digest", "", command)

    if text in {
        "projects",
        "my projects",
        "active projects",
        "what are my projects",
        "what are my projects?",
        "list projects",
        "list my projects",
    }:
        return _dispatch_action("list_projects", "", command)

    for prefix in ("add project ", "create project ", "track project "):
        if text.startswith(prefix):
            return _dispatch_action("add_project", _strip_prefix(command, prefix), command)

    next_action_match = re.match(
        r"^(?:set\s+)?next action for (.+?) (?:to|is) (.+)$",
        command,
        flags=re.IGNORECASE,
    )
    if next_action_match:
        target = f"{next_action_match.group(1)} to {next_action_match.group(2)}"
        return _dispatch_action("set_project_next_action", target, command)

    status_match = re.match(
        r"^(?:set|update|mark) project (.+?) (?:status )?(?:to|as|is) (.+)$",
        command,
        flags=re.IGNORECASE,
    )
    if status_match:
        target = f"{status_match.group(1)} to {status_match.group(2)}"
        return _dispatch_action("set_project_status", target, command)

    if text in {
        "operator status",
        "supervisor status",
        "operator jobs",
        "show operator jobs",
        "list operator jobs",
        "supervised jobs",
    }:
        return _dispatch_action("list_operator_jobs", "", command)

    for prefix in (
        "create operator job ",
        "queue operator job ",
        "start operator job ",
        "create supervised task ",
        "start supervised task ",
        "queue supervised task ",
        "have jarvis work on ",
    ):
        if text.startswith(prefix):
            return _dispatch_action("create_operator_job", _strip_prefix(command, prefix), command)

    for prefix in ("cancel operator job ", "stop operator job ", "cancel supervised task "):
        if text.startswith(prefix):
            return _dispatch_action("cancel_operator_job", _strip_prefix(command, prefix), command)

    for prefix in ("operator status ", "supervisor status ", "status for operator job "):
        if text.startswith(prefix):
            return _dispatch_action("operator_status", _strip_prefix(command, prefix), command)
    if text in {"tts status", "voice status", "what voice are you using", "what voice are you using?"}:
        return _dispatch_action("tts_status", "", command)

    if text in {
        "mode status",
        "assistant mode status",
        "what mode are you in",
        "what mode are you in?",
        "which mode are you in",
        "which mode are you in?",
    }:
        return _dispatch_action("assistant_mode_status", "", command)

    mode_request = _route_mode_request(text, command)
    if mode_request is not None:
        return mode_request

    if text in {"mute jarvis", "turn tts off", "turn voice off", "disable tts"}:
        return _dispatch_action("set_tts_enabled", "off", command)

    if text in {"unmute jarvis", "turn tts on", "turn voice on", "enable tts"}:
        return _dispatch_action("set_tts_enabled", "on", command)

    if re.search(r"\b(?:use|switch to|enable|turn on)\b.*\b(?:elevenlabs|eleven labs|11labs|11 labs)\b", text):
        return _dispatch_action("set_tts_provider", "elevenlabs", command)

    voice_match = re.match(
        r"^(?:use|switch to|set)\s+(?:the\s+)?(?:elevenlabs|eleven labs|11labs|11 labs)?\s*voice\s+(?:to\s+)?(.+)$",
        command,
        flags=re.IGNORECASE,
    )
    if voice_match:
        return _dispatch_action("set_elevenlabs_voice", voice_match.group(1).strip(), command)

    if re.search(r"\b(?:use|switch to)\b.*\b(?:windows|system|default)\b.*\bvoice\b", text):
        return _dispatch_action("set_tts_provider", "windows", command)

    if re.search(r"\b(?:use|switch to)\b.*\b(?:local|pyttsx3)\b.*\bvoice\b", text):
        return _dispatch_action("set_tts_provider", "local", command)

    config = load_device_config()

    # 2) Known websites - checked before the generic "open my <file>" rule so
    #    that "open my email" opens Gmail instead of searching for a file.
    site = _match_config_key(text, config.get("websites", {}).keys())
    if site and re.search(_OPEN_VERBS, text):
        return _dispatch_action("open_website", site, command)

    # 3) Known apps
    app = _match_config_key(text, config.get("apps", {}).keys())
    if app and re.search(_OPEN_VERBS, text):
        return _dispatch_action("open_app", app, command)

    # 4) Browser searches
    youtube_match = re.match(
        r"^(?:find|search(?: for)?|look up)\s+(.+?)\s+(?:on|in)\s+(?:youtube|you tube|you)$",
        text,
    )
    if youtube_match:
        return _dispatch_action("search_youtube", youtube_match.group(1), command)

    web_match = re.match(
        r"^(?:search(?: web| google)? for|google|look up)\s+(.+?)(?:\s+(?:online|on google|on the web))?$",
        text,
    )
    if web_match:
        return _dispatch_action("search_web", web_match.group(1), command)

    if text.startswith("google "):
        return _dispatch_action("search_web", _strip_prefix(command, "google "), command)
    if text.startswith("search web for "):
        return _dispatch_action("search_web", _strip_prefix(command, "search web for "), command)
    if text.startswith("search google for "):
        return _dispatch_action("search_web", _strip_prefix(command, "search google for "), command)
    if text.startswith("search youtube for "):
        return _dispatch_action("search_youtube", _strip_prefix(command, "search youtube for "), command)
    if text.startswith("youtube "):
        return _dispatch_action("search_youtube", _strip_prefix(command, "youtube "), command)

    # 5) Newest file: "open the newest resume"
    if text.startswith("open the newest "):
        return _dispatch_action("open_file", _strip_prefix(command, "open the newest "), command)

    # 6) File search: "find resume", "search for taxes"
    if text.startswith("find "):
        return _dispatch_action("search_files", _strip_prefix(command, "find "), command)
    if text.startswith("search for "):
        return _dispatch_action("search_files", _strip_prefix(command, "search for "), command)
    if text.startswith("search "):
        return _dispatch_action("search_files", _strip_prefix(command, "search "), command)

    # 7) Open best-matching file: "open my resume", "open the resume"
    if text.startswith("open my "):
        return _dispatch_action("open_file", _strip_prefix(command, "open my "), command)
    if text.startswith("open the "):
        return _dispatch_action("open_file", _strip_prefix(command, "open the "), command)

    return None


def route_command(command: str, allow_llm: bool = True) -> str:
    text = _normalize(command)

    pending = handle_pending(command, _dispatch_action)
    if pending is not None:
        return pending

    # Deterministic local rules first (fast, free, predictable)...
    local = _local_route(text, command)
    if local is not None:
        return local

    if not allow_llm:
        log_action("unknown", command, "unhandled", "LLM router disabled for current assistant mode.", command)
        return (
            "I do not have a local skill for that yet. In assist mode I can still handle "
            "configured apps, sites, searches, tasks, projects, reminders, Gmail status, and daily briefs."
        )

    # ...then the LLM router as a flexible fallback.
    try:
        decision = llm_route(command)
    except Exception as exc:
        reason = f"LLM router unavailable: {exc}"
        log_action("unknown", command, "failed", reason, command)
        return (
            "I could not reach the LLM router, so I stayed local. "
            "Try a configured app, site, search, task, project, reminder, Gmail status, or daily brief."
        )
    action = decision.get("action", "unknown")
    target = decision.get("target", "")
    reason = decision.get("reason", "")

    if action == "unknown":
        log_action("unknown", command, "unhandled", reason, command)
        return f"I am not sure how to handle that yet. Reason: {reason}"

    return _dispatch_action(action, target, command)
