import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from core.config import load_device_config

load_dotenv(override=True)

def _client() -> OpenAI:
    load_dotenv(override=True)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Create .env from .env.example, "
            "or use assist mode for local-only commands."
        )
    return OpenAI(api_key=api_key)

SYSTEM_PROMPT = """
You are Jarvis, a local Windows desktop assistant.

Your job is to translate the user's natural language command into one JSON action.

Available actions:
- open_app
- open_website
- search_files
- open_folder
- search_web
- search_youtube
- daily_brief
- add_task
- list_tasks
- complete_task
- add_reminder
- list_reminders
- complete_reminder
- gmail_digest
- gmail_status
- gmail_connect
- add_project
- list_projects
- set_project_status
- set_project_next_action
- set_tts_provider
- set_tts_enabled
- tts_status
- set_elevenlabs_voice
- set_assistant_mode
- assistant_mode_status
- unknown

Rules:
- Return ONLY valid JSON.
- Do not explain.
- Do not include markdown.
- Choose open_website for email, Gmail, GitHub, AWS, LinkedIn, Indeed, Handshake, etc.
- Choose open_app for local Windows applications like Chrome, Opera, VS Code, PowerShell.
- Choose search_files when the user wants to find a local file.
- Choose search_web when the user wants to search the web or look something up online.
- Choose search_youtube when the user wants to search YouTube or find videos.
- Choose daily_brief when the user asks what to focus on, asks for a morning or daily brief, or asks what schoolwork is present.
- Choose add_task when the user asks you to remember, add, create, or track a task.
- Choose list_tasks when the user asks what tasks they have.
- Choose complete_task when the user asks to complete, finish, or mark a task done.
- Choose add_reminder when the user asks you to remind them about something.
- Choose list_reminders when the user asks what reminders they have.
- Choose complete_reminder when the user asks to complete, finish, or mark a reminder done.
- Choose gmail_digest when the user asks to check Gmail, check email, read important emails, or summarize recent email.
- Choose gmail_status when the user asks whether Gmail is configured or connected.
- Choose gmail_connect when the user asks to connect or authorize Gmail.
- Choose add_project when the user asks you to add, create, remember, or track a project.
- Choose list_projects when the user asks what projects they have.
- Choose set_project_status when the user asks to change a project's status.
- Choose set_project_next_action when the user asks to set or update a project's next action.
- Choose set_tts_provider when the user asks to switch voices or use ElevenLabs, Windows, or local TTS.
- Choose set_tts_enabled when the user asks to mute, unmute, turn on, or turn off spoken responses.
- Choose tts_status when the user asks what voice or text-to-speech provider is configured.
- Choose set_elevenlabs_voice when the user asks to switch to a named configured ElevenLabs voice.
- Choose set_assistant_mode when the user asks to switch to command, conversation, push-to-talk, or assist mode.
- Choose assistant_mode_status when the user asks what Jarvis mode is active.
- If unsure, use unknown.

JSON format:
{
  "action": "open_website",
  "target": "gmail",
  "reason": "User wants to open email"
}
"""


def get_available_context() -> str:
    config = load_device_config()

    apps = list(config.get("apps", {}).keys())
    websites = list(config.get("websites", {}).keys())
    folders = config.get("allowed_folders", [])

    return f"""
Available apps: {apps}
Available websites: {websites}
Allowed folders: {folders}
"""


def llm_route(command: str) -> dict:
    context = get_available_context()

    response = _client().chat.completions.create(
        model=os.getenv("JARVIS_MODEL", "gpt-4.1-mini"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": context},
            {"role": "user", "content": command},
        ],
        temperature=0,
    )

    content = response.choices[0].message.content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "action": "unknown",
            "target": command,
            "reason": "The model did not return valid JSON."
        }
