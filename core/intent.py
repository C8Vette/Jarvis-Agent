from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from core.modes import ModeSettings


IntentKind = Literal["command", "chat", "small_talk", "stop"]


@dataclass(frozen=True)
class IntentDecision:
    kind: IntentKind
    text: str
    reason: str = ""
    should_continue_session: bool = True


COMMAND_STARTERS = {
    "add",
    "authorize",
    "brief",
    "check",
    "complete",
    "connect",
    "create",
    "find",
    "finish",
    "google",
    "launch",
    "list",
    "look",
    "mark",
    "mute",
    "open",
    "read",
    "remember",
    "remind",
    "run",
    "search",
    "set",
    "show",
    "start",
    "switch",
    "unmute",
    "use",
    "youtube",
}


COMMAND_PATTERNS = [
    r"\b(?:daily|morning)\s+brief\b",
    r"\bwhat\s+(?:are|do)\s+my\s+(?:tasks|projects|reminders)\b",
    r"\bwhat\s+(?:should|do)\s+i\s+(?:focus|need)\b",
    r"\bwhat\s+schoolwork\b",
    r"\b(?:gmail|email)\s+(?:status|digest)\b",
    r"\b(?:conversation|command|assist|push\s+to\s+talk|push-to-talk)\s+mode\b",
]


CHAT_PATTERNS = [
    r"^(?:hi|hey|hello)(?:\s+jarvis)?(?:[,.!?]|\s|$)",
    r"\bhow\s+are\s+you\b",
    r"\bhow(?:'s| is)\s+it\s+going\b",
    r"\bwhat'?s\s+up\b",
    r"\bwho\s+are\s+you\b",
    r"\bwhat\s+can\s+you\s+do\b",
    r"\bcan\s+we\s+talk\b",
    r"\bi\s+(?:am|feel|felt|have been)\b",
]


SMALL_TALK = {
    "ok",
    "okay",
    "yeah",
    "yes",
    "thanks",
    "thank you",
    "hello",
    "hi",
}


STOP_SESSION_PHRASES = {
    "cancel",
    "never mind",
    "nevermind",
    "stop",
    "stop listening",
    "that's all",
    "that is all",
    "stand by",
    "go back to sleep",
}


def decide_intent(text: str, mode: ModeSettings, has_history: bool = False) -> IntentDecision:
    command = text.strip()
    normalized = _normalize(command)

    if not normalized:
        return IntentDecision("small_talk", command, "empty speech")

    if normalized in STOP_SESSION_PHRASES:
        return IntentDecision("stop", command, "session stop phrase", should_continue_session=False)

    if normalized in SMALL_TALK:
        return IntentDecision("small_talk", command, "small talk")

    if _looks_like_command(normalized):
        return IntentDecision("command", command, "command pattern")

    if mode.name == "conversation":
        if _looks_like_chat(normalized):
            return IntentDecision("chat", command, "chat pattern")
        if has_history and _looks_like_followup(normalized):
            return IntentDecision("chat", command, "conversation follow-up")
        if _looks_like_question(normalized):
            return IntentDecision("chat", command, "general question in conversation mode")

    if mode.name == "assist":
        return IntentDecision("command", command, "assist mode only routes local commands")

    return IntentDecision("command", command, "default to command mode")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower()).strip(" .!?")


def _looks_like_command(text: str) -> bool:
    first_word = text.split(" ", 1)[0]
    if first_word in COMMAND_STARTERS:
        return True
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in COMMAND_PATTERNS)


def _looks_like_chat(text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in CHAT_PATTERNS)


def _looks_like_question(text: str) -> bool:
    return bool(re.match(r"^(?:who|what|when|where|why|how|can|could|would|should|do|does|did|is|are)\b", text))


def _looks_like_followup(text: str) -> bool:
    return bool(
        re.match(
            r"^(?:and|also|but|so|then|what about|how about|that|it|they|he|she|we|you)\b",
            text,
        )
    )
