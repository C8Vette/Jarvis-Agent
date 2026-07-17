from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.config import load_device_config


DEFAULT_MODE = "command"


MODE_LABELS = {
    "command": "Command",
    "conversation": "Conversation",
    "push_to_talk": "Push-to-Talk",
    "assist": "Assist",
}


MODE_DESCRIPTIONS = {
    "command": "Wake word, one command, one response. This is the stable default.",
    "conversation": "Wake word opens a short follow-up session for more natural back-and-forth.",
    "push_to_talk": "Manual listen trigger for deliberate voice input without wake-word detection.",
    "assist": "Lower-cost local mode that skips the LLM router and only uses configured skills.",
}


DEFAULT_MODES_CONFIG: dict[str, Any] = {
    "active": DEFAULT_MODE,
    "modes": {
        "command": {
            "enabled": True,
            "use_llm_router": True,
            "speak_responses": True,
            "continuous_session": False,
            "wake_word_required": True,
            "session_idle_timeout_seconds": 18.0,
            "session_max_turns": 1,
        },
        "conversation": {
            "enabled": True,
            "use_llm_router": True,
            "speak_responses": True,
            "continuous_session": True,
            "wake_word_required": True,
            "session_idle_timeout_seconds": 22.0,
            "session_max_turns": 8,
        },
        "push_to_talk": {
            "enabled": True,
            "use_llm_router": True,
            "speak_responses": True,
            "continuous_session": False,
            "wake_word_required": False,
            "session_idle_timeout_seconds": 30.0,
            "session_max_turns": 1,
        },
        "assist": {
            "enabled": True,
            "use_llm_router": False,
            "speak_responses": True,
            "continuous_session": False,
            "wake_word_required": True,
            "session_idle_timeout_seconds": 18.0,
            "session_max_turns": 1,
        },
    },
    "realtime": {
        "enabled": False,
        "provider": "openai",
        "model": "gpt-4o-realtime-preview",
        "session_timeout_seconds": 600,
        "idle_timeout_seconds": 45,
        "requires_backend_proxy": True,
    },
}


@dataclass(frozen=True)
class ModeSettings:
    name: str
    label: str
    description: str
    enabled: bool = True
    use_llm_router: bool = True
    speak_responses: bool = True
    continuous_session: bool = False
    wake_word_required: bool = True
    session_idle_timeout_seconds: float = 18.0
    session_max_turns: int = 1


def load_modes_config() -> dict[str, Any]:
    config = load_device_config()
    current = config.get("assistant_modes", {})
    return merge_modes_config(current)


def merge_modes_config(value: object) -> dict[str, Any]:
    merged = {
        "active": DEFAULT_MODES_CONFIG["active"],
        "modes": {
            name: dict(settings)
            for name, settings in DEFAULT_MODES_CONFIG["modes"].items()
        },
        "realtime": dict(DEFAULT_MODES_CONFIG["realtime"]),
    }
    if not isinstance(value, dict):
        return merged

    active = str(value.get("active", merged["active"])).strip().lower()
    active = normalize_mode_name(active) or DEFAULT_MODE
    merged["active"] = active

    incoming_modes = value.get("modes", {})
    if isinstance(incoming_modes, dict):
        for raw_name, raw_settings in incoming_modes.items():
            name = normalize_mode_name(str(raw_name))
            if not name or name not in merged["modes"] or not isinstance(raw_settings, dict):
                continue
            merged["modes"][name].update(_clean_mode_settings(raw_settings))

    incoming_realtime = value.get("realtime", {})
    if isinstance(incoming_realtime, dict):
        merged["realtime"].update(_clean_realtime_settings(incoming_realtime))

    return merged


def get_active_mode_name() -> str:
    return load_modes_config().get("active", DEFAULT_MODE)


def load_mode_settings(mode_name: str | None = None) -> ModeSettings:
    modes_config = load_modes_config()
    name = normalize_mode_name(mode_name or modes_config.get("active")) or DEFAULT_MODE
    if name not in modes_config["modes"]:
        name = DEFAULT_MODE
    settings = modes_config["modes"][name]
    return ModeSettings(
        name=name,
        label=MODE_LABELS.get(name, name.replace("_", " ").title()),
        description=MODE_DESCRIPTIONS.get(name, ""),
        enabled=bool(settings.get("enabled", True)),
        use_llm_router=bool(settings.get("use_llm_router", True)),
        speak_responses=bool(settings.get("speak_responses", True)),
        continuous_session=bool(settings.get("continuous_session", False)),
        wake_word_required=bool(settings.get("wake_word_required", True)),
        session_idle_timeout_seconds=float(settings.get("session_idle_timeout_seconds", 18.0)),
        session_max_turns=max(1, int(settings.get("session_max_turns", 1))),
    )


def normalize_mode_name(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "cheap": "assist",
        "cheap_command": "assist",
        "cost_saver": "assist",
        "cost_saving": "assist",
        "ptt": "push_to_talk",
        "push": "push_to_talk",
        "push_to_talk_mode": "push_to_talk",
        "talk": "conversation",
        "conversational": "conversation",
        "realtime": "conversation",
        "real_time": "conversation",
        "default": "command",
        "commands": "command",
    }
    return aliases.get(normalized, normalized)


def mode_options() -> dict[str, dict[str, str]]:
    return {
        name: {
            "label": MODE_LABELS.get(name, name.replace("_", " ").title()),
            "description": MODE_DESCRIPTIONS.get(name, ""),
        }
        for name in DEFAULT_MODES_CONFIG["modes"]
    }


def _clean_mode_settings(raw: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    schema = {
        "enabled": bool,
        "use_llm_router": bool,
        "speak_responses": bool,
        "continuous_session": bool,
        "wake_word_required": bool,
        "session_idle_timeout_seconds": float,
        "session_max_turns": int,
    }
    for key, value_type in schema.items():
        if key not in raw:
            continue
        if value_type is bool:
            cleaned[key] = bool(raw[key])
        elif value_type is int:
            cleaned[key] = max(1, int(raw[key]))
        elif value_type is float:
            cleaned[key] = max(1.0, float(raw[key]))
    return cleaned


def _clean_realtime_settings(raw: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    schema = {
        "enabled": bool,
        "provider": str,
        "model": str,
        "session_timeout_seconds": int,
        "idle_timeout_seconds": int,
        "requires_backend_proxy": bool,
    }
    for key, value_type in schema.items():
        if key not in raw:
            continue
        if value_type is bool:
            cleaned[key] = bool(raw[key])
        elif value_type is int:
            cleaned[key] = max(1, int(raw[key]))
        else:
            cleaned[key] = str(raw[key]).strip()
    return cleaned
