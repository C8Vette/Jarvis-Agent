"""Speech input/output helpers for Jarvis voice mode."""

from __future__ import annotations

import os
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

import httpx
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

from core.config import load_device_config

load_dotenv(override=True)

SAMPLE_RATE = 16000


def write_wav(path: Path, audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    """Write mono int16 PCM audio to a WAV file."""
    pcm = np.asarray(audio, dtype=np.int16)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())


def transcribe_audio(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> str:
    """Transcribe recorded speech with OpenAI audio transcription."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return ""

    client = OpenAI(api_key=api_key)
    model = os.getenv("JARVIS_TRANSCRIBE_MODEL", "whisper-1")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = Path(tmp.name)

    try:
        write_wav(path, audio, sample_rate)
        with path.open("rb") as audio_file:
            response = client.audio.transcriptions.create(model=model, file=audio_file)
        return getattr(response, "text", "").strip()
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


@dataclass
class TTSSettings:
    enabled: bool = True
    provider: str = "windows"
    fallback_provider: str = "local"
    local_rate: int = 185
    elevenlabs_api_key_env_var: str = "ELEVENLABS_API_KEY"
    elevenlabs_active_voice: str = ""
    elevenlabs_voice_id: str = ""
    elevenlabs_model_id: str = "eleven_multilingual_v2"
    elevenlabs_output_format: str = "pcm_16000"
    elevenlabs_stability: float = 0.45
    elevenlabs_similarity_boost: float = 0.75

    @classmethod
    def from_config(cls) -> "TTSSettings":
        config = load_device_config().get("tts", {})
        local = config.get("local", {})
        elevenlabs = config.get("elevenlabs", {})
        active_voice = str(elevenlabs.get("active_voice", "")).strip()
        profiles = elevenlabs.get("profiles", {})
        profile_voice_id = ""
        if active_voice and isinstance(profiles, dict):
            active_profile = profiles.get(active_voice, {})
            if isinstance(active_profile, dict):
                profile_voice_id = str(active_profile.get("voice_id", "")).strip()

        settings = cls(
            enabled=bool(config.get("enabled", True)),
            provider=str(config.get("provider", "local")),
            fallback_provider=str(config.get("fallback_provider", "local")),
            local_rate=int(local.get("rate", 185)),
            elevenlabs_api_key_env_var=str(elevenlabs.get("api_key_env", "ELEVENLABS_API_KEY")),
            elevenlabs_active_voice=active_voice,
            elevenlabs_voice_id=profile_voice_id or str(elevenlabs.get("voice_id", "")),
            elevenlabs_model_id=str(elevenlabs.get("model_id", "eleven_multilingual_v2")),
            elevenlabs_output_format=str(elevenlabs.get("output_format", "pcm_16000")),
            elevenlabs_stability=float(elevenlabs.get("stability", 0.45)),
            elevenlabs_similarity_boost=float(elevenlabs.get("similarity_boost", 0.75)),
        )

        settings.enabled = _env_bool("JARVIS_TTS_ENABLED", settings.enabled)
        settings.provider = os.getenv("JARVIS_TTS_PROVIDER", settings.provider)
        settings.fallback_provider = os.getenv("JARVIS_TTS_FALLBACK_PROVIDER", settings.fallback_provider)
        settings.local_rate = _env_int("JARVIS_TTS_RATE", settings.local_rate)
        settings.elevenlabs_active_voice = os.getenv("ELEVENLABS_ACTIVE_VOICE", settings.elevenlabs_active_voice)
        settings.elevenlabs_voice_id = os.getenv("ELEVENLABS_VOICE_ID", settings.elevenlabs_voice_id)
        settings.elevenlabs_model_id = os.getenv("ELEVENLABS_MODEL_ID", settings.elevenlabs_model_id)
        settings.elevenlabs_output_format = os.getenv(
            "ELEVENLABS_OUTPUT_FORMAT", settings.elevenlabs_output_format
        )
        return settings


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value is None else int(value)


class TTSProvider:
    name = "base"
    last_error = ""

    def available(self) -> bool:
        return True

    def say(self, text: str) -> bool:
        raise NotImplementedError


class NullTTSProvider(TTSProvider):
    name = "none"

    def available(self) -> bool:
        return False

    def say(self, text: str) -> bool:
        self.last_error = "TTS provider is disabled"
        return False


class LocalPyttsx3Provider(TTSProvider):
    name = "local"

    def __init__(self, settings: TTSSettings) -> None:
        self._settings = settings
        self._engine = None
        self._attempts = 0
        self._max_attempts = 2
        self.last_error = ""

    def _ensure_engine(self) -> bool:
        if self._engine:
            return True
        if self._attempts >= self._max_attempts:
            return False
        self._attempts += 1
        try:
            import pyttsx3

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self._settings.local_rate)
            self.last_error = ""
        except Exception as exc:
            self.last_error = str(exc)
            self._engine = None
        return self._engine is not None

    def available(self) -> bool:
        return self._ensure_engine()

    def say(self, text: str) -> bool:
        if not self._ensure_engine():
            return False
        self._engine.say(text)
        self._engine.runAndWait()
        return True


class WindowsSpeechProvider(TTSProvider):
    name = "windows"

    def __init__(self, settings: TTSSettings) -> None:
        self._settings = settings
        self.last_error = ""

    def say(self, text: str) -> bool:
        script = (
            "$text = [Console]::In.ReadToEnd(); "
            "Add-Type -AssemblyName System.Speech; "
            "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$speaker.Rate = {max(-10, min(10, int((self._settings.local_rate - 185) / 20)))}; "
            "$speaker.Speak($text);"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                input=text,
                text=True,
                capture_output=True,
                timeout=30,
            )
        except Exception as exc:
            self.last_error = str(exc)
            return False

        if result.returncode != 0:
            self.last_error = (result.stderr or result.stdout or "Windows speech failed").strip()
            return False

        self.last_error = ""
        return True


class ElevenLabsProvider(TTSProvider):
    name = "elevenlabs"

    def __init__(self, settings: TTSSettings) -> None:
        self._settings = settings
        self._api_key = os.getenv(settings.elevenlabs_api_key_env_var, "")
        self.last_error = ""
        self._disabled_for_session = False

    def available(self) -> bool:
        if self._disabled_for_session:
            self.last_error = ""
            return False
        if not self._api_key:
            self.last_error = f"missing {self._settings.elevenlabs_api_key_env_var}"
            return False
        if not self._settings.elevenlabs_voice_id:
            self.last_error = "missing ElevenLabs voice_id"
            return False
        self.last_error = ""
        return True

    def say(self, text: str) -> bool:
        if not self.available():
            return False

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self._settings.elevenlabs_voice_id}"
        params = {"output_format": self._settings.elevenlabs_output_format}
        payload = {
            "text": text,
            "model_id": self._settings.elevenlabs_model_id,
            "voice_settings": {
                "stability": self._settings.elevenlabs_stability,
                "similarity_boost": self._settings.elevenlabs_similarity_boost,
            },
        }
        headers = {
            "xi-api-key": self._api_key,
            "accept": "audio/wav" if "pcm" in self._settings.elevenlabs_output_format else "audio/mpeg",
            "content-type": "application/json",
        }

        try:
            response = httpx.post(url, params=params, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            self._play_audio(response.content)
            return True
        except httpx.HTTPStatusError as exc:
            details = exc.response.text[:300] if exc.response is not None else ""
            self.last_error = f"HTTP {exc.response.status_code}: {details}"
            if exc.response.status_code == 402 or "paid_plan_required" in details:
                self._disabled_for_session = True
            return False
        except Exception as exc:
            self.last_error = str(exc)
            return False

    def _play_audio(self, audio: bytes) -> None:
        if self._settings.elevenlabs_output_format.startswith("pcm_"):
            samples = np.frombuffer(audio, dtype=np.int16)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                path = Path(tmp.name)
            try:
                write_wav(path, samples, SAMPLE_RATE)
                import winsound

                winsound.PlaySound(str(path), winsound.SND_FILENAME)
            finally:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            return

        # Fallback for non-PCM formats: let Windows pick the default player.
        suffix = ".mp3"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio)
            path = Path(tmp.name)
        os.startfile(path)


class Speaker:
    """Config-driven TTS facade with provider fallback."""

    def __init__(self, settings: TTSSettings | None = None) -> None:
        self.settings = settings or TTSSettings.from_config()
        self.primary = self._build_provider(self.settings.provider)
        self.fallback = self._build_provider(self.settings.fallback_provider)
        self.last_error = ""
        self.last_provider_used = ""

    @property
    def provider_name(self) -> str:
        if self.primary.available():
            return self.primary.name
        if self.fallback.available():
            return self.fallback.name
        return "none"

    @property
    def provider_status(self) -> str:
        active = self.provider_name
        status = f"{active} (requested: {self.primary.name}, fallback: {self.fallback.name})"
        if active == "none":
            errors = []
            if self.primary.last_error:
                errors.append(f"{self.primary.name}: {self.primary.last_error}")
            if self.fallback.last_error:
                errors.append(f"{self.fallback.name}: {self.fallback.last_error}")
            if errors:
                status += " unavailable: " + "; ".join(errors)
        return status

    def _build_provider(self, name: str) -> TTSProvider:
        normalized = name.strip().lower()
        if normalized in {"", "none", "off", "disabled"}:
            return NullTTSProvider()
        if normalized in {"local", "pyttsx3"}:
            return LocalPyttsx3Provider(self.settings)
        if normalized in {"windows", "sapi", "system"}:
            return WindowsSpeechProvider(self.settings)
        if normalized in {"elevenlabs", "eleven_labs", "11labs"}:
            return ElevenLabsProvider(self.settings)
        return NullTTSProvider()

    def say(self, text: str) -> bool:
        self.last_error = ""
        self.last_provider_used = ""
        if not self.settings.enabled or not text.strip():
            return True

        if self.primary.available():
            if self.primary.say(text):
                self.last_provider_used = self.primary.name
                return True
            if self.primary.last_error:
                self.last_error = f"{self.primary.name}: {self.primary.last_error}"
        elif self.primary.last_error:
            self.last_error = f"{self.primary.name}: {self.primary.last_error}"

        if self.fallback.available():
            if self.fallback.say(text):
                self.last_provider_used = self.fallback.name
                return True
            if self.fallback.last_error:
                fallback_error = f"{self.fallback.name}: {self.fallback.last_error}"
                self.last_error = f"{self.last_error}; {fallback_error}" if self.last_error else fallback_error
        elif self.fallback.last_error:
            fallback_error = f"{self.fallback.name}: {self.fallback.last_error}"
            self.last_error = f"{self.last_error}; {fallback_error}" if self.last_error else fallback_error

        return False
