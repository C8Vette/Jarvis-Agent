import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from core.config import load_device_config

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
You are Jarvis, a local Windows desktop assistant.

Your job is to translate the user's natural language command into one JSON action.

Available actions:
- open_app
- open_website
- search_files
- unknown

Rules:
- Return ONLY valid JSON.
- Do not explain.
- Do not include markdown.
- Choose open_website for email, Gmail, GitHub, AWS, LinkedIn, Indeed, Handshake, etc.
- Choose open_app for local Windows applications like Chrome, Opera, VS Code, PowerShell.
- Choose search_files when the user wants to find a local file.
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

    response = client.chat.completions.create(
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