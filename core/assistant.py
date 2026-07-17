from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from core.chat import chat_response
from core.intent import IntentDecision, decide_intent
from core.modes import ModeSettings, load_mode_settings
from core.router import route_command


@dataclass
class AssistantTurn:
    user_text: str
    response: str
    mode: str
    source: str
    intent: str = "command"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class AssistantSession:
    """Shared Jarvis runtime used by typed, voice, and future realtime modes."""

    def __init__(self, mode_name: str | None = None, source: str = "local") -> None:
        self.requested_mode = mode_name
        self.mode = load_mode_settings(mode_name)
        self.source = source
        self.turns: list[AssistantTurn] = []

    @property
    def mode_name(self) -> str:
        return self.mode.name

    @property
    def should_speak(self) -> bool:
        return self.mode.speak_responses

    def process_text(self, text: str) -> str:
        command = text.strip()
        if not command:
            return "I did not catch that."

        decision = decide_intent(command, self.mode, has_history=bool(self.turns))
        if decision.kind == "small_talk":
            response = self._small_talk_response(command)
        elif decision.kind == "stop":
            response = "I'll stand by."
        elif decision.kind == "chat":
            response = chat_response(command, self.turns, allow_llm=self.mode.use_llm_router)
        else:
            response = route_command(command, allow_llm=self.mode.use_llm_router)

        if self.mode.name == "conversation" and _router_missed_command(response) and self.mode.use_llm_router:
            response = chat_response(command, self.turns, allow_llm=True)
            decision = IntentDecision("chat", command, "router missed; conversation fallback")

        self.turns.append(
            AssistantTurn(
                user_text=command,
                response=response,
                mode=self.mode.name,
                source=self.source,
                intent=decision.kind,
            )
        )
        return response

    def is_stop_phrase(self, text: str) -> bool:
        return decide_intent(text, self.mode).kind == "stop"

    def refresh_mode(self) -> ModeSettings:
        self.mode = load_mode_settings(self.requested_mode)
        return self.mode

    def _small_talk_response(self, text: str) -> str:
        if self.mode.name == "conversation":
            return chat_response(text, self.turns, allow_llm=False)
        return "Ready when you are."


def _router_missed_command(response: str) -> bool:
    normalized = response.lower()
    return (
        normalized.startswith("i am not sure how to handle that yet")
        or normalized.startswith("i could not reach the llm router")
        or normalized.startswith("i do not have a local skill for that yet")
    )
