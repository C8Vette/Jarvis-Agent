from __future__ import annotations

from core.config import load_device_config, save_device_config
from core.modes import MODE_LABELS, load_mode_settings, merge_modes_config, normalize_mode_name
from core.speech import TTSSettings

PROVIDER_ALIASES = {
    "elevenlabs": "elevenlabs",
    "eleven labs": "elevenlabs",
    "11labs": "elevenlabs",
    "11 labs": "elevenlabs",
    "windows": "windows",
    "system": "windows",
    "default": "windows",
    "local": "local",
    "pyttsx3": "local",
    "none": "none",
    "off": "none",
}


def _load_tts_config() -> tuple[dict, dict]:
    config = load_device_config()
    tts = config.setdefault("tts", {})
    tts.setdefault("enabled", True)
    tts.setdefault("provider", "windows")
    tts.setdefault("fallback_provider", "local")
    return config, tts


def set_tts_provider(target: str) -> str:
    provider = PROVIDER_ALIASES.get(target.strip().lower())
    if not provider:
        supported = ", ".join(["elevenlabs", "windows", "local", "none"])
        return f"I do not recognize that voice provider. Supported providers: {supported}."

    config, tts = _load_tts_config()
    tts["provider"] = provider
    tts["enabled"] = provider != "none"
    save_device_config(config)
    return f"TTS provider set to {provider}."


def set_tts_enabled(target: str) -> str:
    normalized = target.strip().lower()
    enabled = normalized in {"on", "true", "yes", "enabled", "enable", "unmute"}

    config, tts = _load_tts_config()
    tts["enabled"] = enabled
    save_device_config(config)
    return "TTS enabled." if enabled else "TTS muted."


def tts_status(_: str = "") -> str:
    settings = TTSSettings.from_config()
    state = "enabled" if settings.enabled else "muted"
    voice = f" Voice: {settings.elevenlabs_active_voice}." if settings.elevenlabs_active_voice else ""
    return (
        f"TTS is {state}. Provider: {settings.provider}. "
        f"Fallback: {settings.fallback_provider}.{voice}"
    )


def set_elevenlabs_voice(target: str) -> str:
    voice_name = target.strip().lower()
    if not voice_name:
        return "Tell me which ElevenLabs voice profile to use."

    config, tts = _load_tts_config()
    elevenlabs = tts.setdefault("elevenlabs", {})
    profiles = elevenlabs.setdefault("profiles", {})
    match = None
    for name in profiles:
        if name.lower() == voice_name:
            match = name
            break

    if not match:
        known = ", ".join(profiles.keys()) or "none configured"
        return f"I could not find that ElevenLabs voice profile. Configured voices: {known}."

    elevenlabs["active_voice"] = match
    voice_id = profiles.get(match, {}).get("voice_id", "")
    if voice_id:
        elevenlabs["voice_id"] = voice_id
    tts["provider"] = "elevenlabs"
    tts["enabled"] = True
    save_device_config(config)
    return f"ElevenLabs voice set to {match}."


def set_assistant_mode(target: str) -> str:
    requested = normalize_mode_name(target)
    if not requested:
        return "Tell me which mode to use: command, conversation, push-to-talk, or assist."

    config = load_device_config()
    modes = merge_modes_config(config.get("assistant_modes", {}))
    if requested not in modes["modes"]:
        known = ", ".join(MODE_LABELS.values())
        return f"I do not recognize that mode. Available modes: {known}."

    if not modes["modes"][requested].get("enabled", True):
        return f"{MODE_LABELS.get(requested, requested)} mode is configured but disabled."

    modes["active"] = requested
    config["assistant_modes"] = modes
    save_device_config(config)
    return f"Assistant mode set to {MODE_LABELS.get(requested, requested)}."


def assistant_mode_status(_: str = "") -> str:
    mode = load_mode_settings()
    llm_state = "LLM routing on" if mode.use_llm_router else "local skills only"
    session_state = "continuous session" if mode.continuous_session else "single command"
    return f"Jarvis is in {mode.label} mode: {session_state}, {llm_state}."
