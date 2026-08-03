from __future__ import annotations

from dataclasses import dataclass

AUTO_ALLOW = "auto_allow"
REQUIRE_CONFIRMATION = "require_confirmation"
BLOCKED = "blocked"


@dataclass(frozen=True)
class ActionDefinition:
    name: str
    description: str
    default_policy: str
    risk: str


ACTION_REGISTRY: dict[str, ActionDefinition] = {
    "daily_brief": ActionDefinition(
        name="daily_brief",
        description="Read configured routine, school, and project context.",
        default_policy=AUTO_ALLOW,
        risk="read_only",
    ),
    "add_task": ActionDefinition(
        name="add_task",
        description="Add a local task to Jarvis memory.",
        default_policy=AUTO_ALLOW,
        risk="local_memory_write",
    ),
    "list_tasks": ActionDefinition(
        name="list_tasks",
        description="List open local tasks from Jarvis memory.",
        default_policy=AUTO_ALLOW,
        risk="read_only",
    ),
    "complete_task": ActionDefinition(
        name="complete_task",
        description="Mark a local task as complete.",
        default_policy=AUTO_ALLOW,
        risk="local_memory_write",
    ),
    "add_reminder": ActionDefinition(
        name="add_reminder",
        description="Add a local reminder to Jarvis memory.",
        default_policy=AUTO_ALLOW,
        risk="local_memory_write",
    ),
    "list_reminders": ActionDefinition(
        name="list_reminders",
        description="List local reminders from Jarvis memory.",
        default_policy=AUTO_ALLOW,
        risk="read_only",
    ),
    "complete_reminder": ActionDefinition(
        name="complete_reminder",
        description="Mark a local reminder as complete.",
        default_policy=AUTO_ALLOW,
        risk="local_memory_write",
    ),
    "gmail_digest": ActionDefinition(
        name="gmail_digest",
        description="Read a metadata-only Gmail digest.",
        default_policy=AUTO_ALLOW,
        risk="email_read",
    ),
    "gmail_status": ActionDefinition(
        name="gmail_status",
        description="Check Gmail integration status.",
        default_policy=AUTO_ALLOW,
        risk="read_only",
    ),
    "gmail_connect": ActionDefinition(
        name="gmail_connect",
        description="Run OAuth to connect a Gmail account.",
        default_policy=REQUIRE_CONFIRMATION,
        risk="account_authorization",
    ),
    "add_project": ActionDefinition(
        name="add_project",
        description="Add a local project to Jarvis memory.",
        default_policy=AUTO_ALLOW,
        risk="local_memory_write",
    ),
    "list_projects": ActionDefinition(
        name="list_projects",
        description="List local projects from Jarvis memory.",
        default_policy=AUTO_ALLOW,
        risk="read_only",
    ),
    "set_project_status": ActionDefinition(
        name="set_project_status",
        description="Update a local project's status.",
        default_policy=AUTO_ALLOW,
        risk="local_memory_write",
    ),
    "set_project_next_action": ActionDefinition(
        name="set_project_next_action",
        description="Update a local project's next action.",
        default_policy=AUTO_ALLOW,
        risk="local_memory_write",
    ),
    "set_tts_provider": ActionDefinition(
        name="set_tts_provider",
        description="Switch Jarvis text-to-speech provider.",
        default_policy=AUTO_ALLOW,
        risk="local_settings_write",
    ),
    "set_tts_enabled": ActionDefinition(
        name="set_tts_enabled",
        description="Enable or mute Jarvis spoken responses.",
        default_policy=AUTO_ALLOW,
        risk="local_settings_write",
    ),
    "tts_status": ActionDefinition(
        name="tts_status",
        description="Read Jarvis text-to-speech settings.",
        default_policy=AUTO_ALLOW,
        risk="read_only",
    ),
    "set_elevenlabs_voice": ActionDefinition(
        name="set_elevenlabs_voice",
        description="Switch the active configured ElevenLabs voice profile.",
        default_policy=AUTO_ALLOW,
        risk="local_settings_write",
    ),
    "set_assistant_mode": ActionDefinition(
        name="set_assistant_mode",
        description="Switch Jarvis between command, conversation, push-to-talk, and assist modes.",
        default_policy=AUTO_ALLOW,
        risk="local_settings_write",
    ),
    "assistant_mode_status": ActionDefinition(
        name="assistant_mode_status",
        description="Read the active Jarvis assistant mode.",
        default_policy=AUTO_ALLOW,
        risk="read_only",
    ),
    "create_operator_job": ActionDefinition(
        name="create_operator_job",
        description="Queue a supervised local operator job without executing external tools.",
        default_policy=AUTO_ALLOW,
        risk="local_memory_write",
    ),
    "list_operator_jobs": ActionDefinition(
        name="list_operator_jobs",
        description="List supervised local operator jobs.",
        default_policy=AUTO_ALLOW,
        risk="read_only",
    ),
    "operator_status": ActionDefinition(
        name="operator_status",
        description="Read status for a supervised operator job.",
        default_policy=AUTO_ALLOW,
        risk="read_only",
    ),
    "cancel_operator_job": ActionDefinition(
        name="cancel_operator_job",
        description="Cancel a supervised local operator job.",
        default_policy=AUTO_ALLOW,
        risk="local_memory_write",
    ),    "open_app": ActionDefinition(
        name="open_app",
        description="Launch a configured local application.",
        default_policy=AUTO_ALLOW,
        risk="local_launch",
    ),
    "open_website": ActionDefinition(
        name="open_website",
        description="Open a configured website or direct URL.",
        default_policy=AUTO_ALLOW,
        risk="browser_launch",
    ),
    "open_folder": ActionDefinition(
        name="open_folder",
        description="Open a local folder.",
        default_policy=AUTO_ALLOW,
        risk="filesystem_read",
    ),
    "search_files": ActionDefinition(
        name="search_files",
        description="Search filenames inside allowed folders.",
        default_policy=AUTO_ALLOW,
        risk="filesystem_read",
    ),
    "open_file": ActionDefinition(
        name="open_file",
        description="Open a best-match file inside allowed folders.",
        default_policy=AUTO_ALLOW,
        risk="filesystem_read",
    ),
    "search_web": ActionDefinition(
        name="search_web",
        description="Open a browser search for a user-provided query.",
        default_policy=AUTO_ALLOW,
        risk="browser_launch",
    ),
    "search_youtube": ActionDefinition(
        name="search_youtube",
        description="Open a YouTube search for a user-provided query.",
        default_policy=AUTO_ALLOW,
        risk="browser_launch",
    ),
    "run_terminal": ActionDefinition(
        name="run_terminal",
        description="Run a terminal command.",
        default_policy=REQUIRE_CONFIRMATION,
        risk="command_execution",
    ),
    "install_package": ActionDefinition(
        name="install_package",
        description="Install software or packages.",
        default_policy=REQUIRE_CONFIRMATION,
        risk="system_change",
    ),
    "send_email": ActionDefinition(
        name="send_email",
        description="Send email or outbound messages.",
        default_policy=REQUIRE_CONFIRMATION,
        risk="external_write",
    ),
    "move_file": ActionDefinition(
        name="move_file",
        description="Move files.",
        default_policy=REQUIRE_CONFIRMATION,
        risk="filesystem_write",
    ),
    "copy_file": ActionDefinition(
        name="copy_file",
        description="Copy files.",
        default_policy=REQUIRE_CONFIRMATION,
        risk="filesystem_write",
    ),
    "delete_file": ActionDefinition(
        name="delete_file",
        description="Delete files.",
        default_policy=REQUIRE_CONFIRMATION,
        risk="destructive_filesystem_write",
    ),
    "change_system_settings": ActionDefinition(
        name="change_system_settings",
        description="Change operating system settings.",
        default_policy=REQUIRE_CONFIRMATION,
        risk="system_change",
    ),
}


def get_action_definition(action: str) -> ActionDefinition | None:
    return ACTION_REGISTRY.get(action)
