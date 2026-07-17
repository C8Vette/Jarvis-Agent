from __future__ import annotations

import os
from typing import Iterable

from dotenv import load_dotenv

from core.config import load_user_config


LOCAL_CHAT_RESPONSES = {
    "how are you": "I'm doing well. I'm here, listening, and ready to help you move through the day.",
    "how are you doing": "I'm doing well. The important part is that I'm listening properly now.",
    "what's up": "I'm here and ready. We can talk, or I can help with tasks, projects, browsing, or your daily brief.",
    "who are you": "I'm Jarvis, your local desktop assistant. Right now I can handle tasks, projects, reminders, apps, sites, searches, and conversation mode.",
    "what can you do": "I can help with tasks, reminders, projects, app and site launching, browser searches, daily briefs, and lightweight conversation.",
    "can we talk": "Yes. I'm here with you. What's on your mind?",
}


def chat_response(prompt: str, history: Iterable[object], allow_llm: bool = True) -> str:
    local = _local_chat_response(prompt)
    if local:
        return local

    if not allow_llm:
        return (
            "I can talk more naturally in conversation mode when LLM chat is available. "
            "Right now I can still help with local tasks, projects, reminders, apps, sites, and searches."
        )

    try:
        return _llm_chat_response(prompt, history)
    except Exception:
        return (
            "I'm here with you. I could not reach the conversation model right now, "
            "but I can still handle local commands and keep the session going."
        )


def _local_chat_response(prompt: str) -> str:
    normalized = prompt.strip().lower().strip(" .!?")
    for key, response in LOCAL_CHAT_RESPONSES.items():
        if key in normalized:
            return response
    if normalized.startswith(("hi", "hey", "hello")):
        return "Hey Ethan. I'm listening."
    if normalized in {"thanks", "thank you"}:
        return "Of course."
    return ""


def _llm_chat_response(prompt: str, history: Iterable[object]) -> str:
    load_dotenv(override=True)
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    user_config = load_user_config()
    name = user_config.get("profile", {}).get("name", "the user")
    recent_messages = []
    for turn in list(history)[-6:]:
        user_text = getattr(turn, "user_text", "")
        response = getattr(turn, "response", "")
        if user_text:
            recent_messages.append({"role": "user", "content": user_text})
        if response:
            recent_messages.append({"role": "assistant", "content": response})

    messages = [
        {
            "role": "system",
            "content": (
                f"You are Jarvis, {name}'s local desktop assistant. "
                "You are warm, concise, practical, and conversational. "
                "Do not claim you performed computer actions unless a tool/action result says so. "
                "Keep replies short enough to be spoken aloud."
            ),
        },
        *recent_messages,
        {"role": "user", "content": prompt},
    ]

    response = client.chat.completions.create(
        model=os.getenv("JARVIS_CHAT_MODEL", os.getenv("JARVIS_MODEL", "gpt-4.1-mini")),
        messages=messages,
        temperature=0.5,
        max_tokens=140,
    )
    return (response.choices[0].message.content or "").strip() or "I'm here."
