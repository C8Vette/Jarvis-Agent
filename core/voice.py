"""Wake-word driven voice loop for Jarvis."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import numpy as np
from rich.console import Console

from core.assistant import AssistantSession
from core.config import load_device_config
from core.speech import SAMPLE_RATE, Speaker, transcribe_audio

console = Console()


@dataclass
class VoiceSettings:
    wake_word: str = "hey jarvis"
    wake_threshold: float = 0.8
    wake_inference_framework: str = "onnx"
    vad_threshold: float = 0.3
    command_seconds: float = 45.0
    start_timeout_seconds: float = 8.0
    silence_seconds: float = 3.0
    min_command_seconds: float = 2.0
    pre_roll_seconds: float = 0.7
    speech_rms_threshold: int = 0
    speech_rms_multiplier: float = 2.4
    min_speech_rms_threshold: int = 120
    prompt_after_wake: bool = False
    wake_response: str = "Yes?"
    listen_delay_seconds: float = 0.0
    audible_cues: bool = True
    listen_cue_hz: int = 880
    done_cue_hz: int = 660
    cue_ms: int = 110
    cooldown_seconds: float = 1.0

    @classmethod
    def from_config(cls) -> "VoiceSettings":
        config = load_device_config().get("voice", {})
        settings = cls()

        for field_name in settings.__dataclass_fields__:
            if field_name in config:
                setattr(settings, field_name, config[field_name])

        settings.wake_word = _env_str("JARVIS_WAKE_WORD", settings.wake_word)
        settings.wake_threshold = _env_float("JARVIS_WAKE_THRESHOLD", settings.wake_threshold)
        settings.wake_inference_framework = _env_str(
            "JARVIS_WAKE_INFERENCE_FRAMEWORK", settings.wake_inference_framework
        )
        settings.vad_threshold = _env_float("JARVIS_VAD_THRESHOLD", settings.vad_threshold)
        settings.command_seconds = _env_float("JARVIS_COMMAND_SECONDS", settings.command_seconds)
        settings.start_timeout_seconds = _env_float(
            "JARVIS_START_TIMEOUT_SECONDS", settings.start_timeout_seconds
        )
        settings.silence_seconds = _env_float("JARVIS_SILENCE_SECONDS", settings.silence_seconds)
        settings.min_command_seconds = _env_float(
            "JARVIS_MIN_COMMAND_SECONDS", settings.min_command_seconds
        )
        settings.pre_roll_seconds = _env_float("JARVIS_PRE_ROLL_SECONDS", settings.pre_roll_seconds)
        settings.speech_rms_threshold = _env_int(
            "JARVIS_SPEECH_RMS_THRESHOLD", settings.speech_rms_threshold
        )
        settings.speech_rms_multiplier = _env_float(
            "JARVIS_SPEECH_RMS_MULTIPLIER", settings.speech_rms_multiplier
        )
        settings.min_speech_rms_threshold = _env_int(
            "JARVIS_MIN_SPEECH_RMS_THRESHOLD", settings.min_speech_rms_threshold
        )
        settings.prompt_after_wake = _env_bool("JARVIS_PROMPT_AFTER_WAKE", settings.prompt_after_wake)
        settings.wake_response = _env_str("JARVIS_WAKE_RESPONSE", settings.wake_response)
        settings.listen_delay_seconds = _env_float(
            "JARVIS_LISTEN_DELAY_SECONDS", settings.listen_delay_seconds
        )
        settings.audible_cues = _env_bool("JARVIS_AUDIBLE_CUES", settings.audible_cues)
        settings.listen_cue_hz = _env_int("JARVIS_LISTEN_CUE_HZ", settings.listen_cue_hz)
        settings.done_cue_hz = _env_int("JARVIS_DONE_CUE_HZ", settings.done_cue_hz)
        settings.cue_ms = _env_int("JARVIS_CUE_MS", settings.cue_ms)
        settings.cooldown_seconds = _env_float("JARVIS_WAKE_COOLDOWN", settings.cooldown_seconds)

        return settings


def _env_str(name: str, default: str) -> str:
    return os.getenv(name, default)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return default if value is None else float(value)


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value is None else int(value)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() not in {"0", "false", "no", "off"}


def _require_audio_stack():
    try:
        import sounddevice as sd
        from openwakeword.model import Model
        import openwakeword.utils
    except ImportError as exc:
        missing = exc.name or "voice dependency"
        raise RuntimeError(
            f"Voice mode needs optional audio packages. Missing: {missing}. "
            "Install requirements-voice.txt, then run again."
        ) from exc

    return sd, Model, openwakeword.utils


def play_cue(frequency: int, duration_ms: int, enabled: bool = True) -> None:
    if not enabled:
        return
    try:
        import winsound

        winsound.Beep(frequency, duration_ms)
    except Exception:
        pass


_TTS_WARNINGS_SHOWN: set[str] = set()


def speak(speaker: Speaker, text: str) -> None:
    if speaker.say(text):
        if speaker.last_error:
            warning = speaker.last_error[:180]
            if warning not in _TTS_WARNINGS_SHOWN:
                _TTS_WARNINGS_SHOWN.add(warning)
                console.print(f"[yellow]Primary TTS warning:[/yellow] {warning}")
        return
    else:
        warning = (speaker.last_error or speaker.provider_status)[:180]
        if warning not in _TTS_WARNINGS_SHOWN:
            _TTS_WARNINGS_SHOWN.add(warning)
            console.print(f"[yellow]TTS failed:[/yellow] {warning}")


def _model_names(prediction: dict) -> list[str]:
    return [name for name, score in prediction.items() if isinstance(score, (int, float))]


def _wake_score(prediction: dict, wake_word: str) -> float:
    if wake_word in prediction:
        return float(prediction[wake_word])

    compact = wake_word.replace(" ", "_")
    if compact in prediction:
        return float(prediction[compact])

    target = wake_word.replace(" ", "").lower()
    for name, score in prediction.items():
        candidate = name.replace("_", "").replace(" ", "").lower()
        if target in candidate:
            return float(score)
    return 0.0


def _rms(frame: np.ndarray) -> float:
    if frame.size == 0:
        return 0.0
    samples = frame.astype(np.float32)
    return float(np.sqrt(np.mean(samples * samples)))


def _trim_silence(audio: np.ndarray, threshold: int, padding_seconds: float = 0.2) -> np.ndarray:
    frame_size = int(SAMPLE_RATE * 0.08)
    padding = int(SAMPLE_RATE * padding_seconds)
    active_frames = []

    for start in range(0, len(audio), frame_size):
        frame = audio[start:start + frame_size]
        if _rms(frame) >= threshold:
            active_frames.append((start, min(start + frame_size, len(audio))))

    if not active_frames:
        return audio

    start = max(0, active_frames[0][0] - padding)
    end = min(len(audio), active_frames[-1][1] + padding)
    return audio[start:end]


def calibrate_noise_floor(stream, seconds: float = 0.8) -> float:
    block_frames = int(SAMPLE_RATE * 0.08)
    target_frames = int(SAMPLE_RATE * seconds)
    frames_read = 0
    rms_values = []

    while frames_read < target_frames:
        frame, _ = stream.read(block_frames)
        chunk = frame.reshape(-1)
        rms_values.append(_rms(chunk))
        frames_read += len(chunk)

    if not rms_values:
        return 0.0
    return float(np.median(rms_values))


def effective_speech_threshold(settings: VoiceSettings, noise_floor: float) -> int:
    if settings.speech_rms_threshold > 0:
        return settings.speech_rms_threshold

    dynamic_threshold = int(noise_floor * settings.speech_rms_multiplier)
    return max(settings.min_speech_rms_threshold, dynamic_threshold)


def record_command(stream, settings: VoiceSettings, speech_threshold: int) -> np.ndarray:
    max_record_frames = int(SAMPLE_RATE * settings.command_seconds)
    max_wait_frames = int(SAMPLE_RATE * settings.start_timeout_seconds)
    block_frames = int(SAMPLE_RATE * 0.12)
    silence_limit = max(1, int(settings.silence_seconds / 0.12))
    min_blocks = max(1, int(settings.min_command_seconds / 0.12))
    frames = []
    heard_speech = False
    silent_blocks = 0
    waited_frames = 0
    speech_frames = 0

    console.print("[dim]Listening for your command...[/dim]")
    play_cue(settings.listen_cue_hz, settings.cue_ms, settings.audible_cues)

    while speech_frames < max_record_frames:
        frame, _ = stream.read(block_frames)
        chunk = frame.reshape(-1).copy()
        is_speech = _rms(chunk) >= speech_threshold

        frames.append(chunk)
        speech_frames += len(chunk)

        if not heard_speech:
            waited_frames += len(chunk)

        if is_speech and not heard_speech:
            heard_speech = True
            waited_frames = 0
            console.print("[dim]Heard speech...[/dim]")

        if heard_speech and not is_speech:
            silent_blocks += 1
        elif is_speech:
            silent_blocks = 0

        if not heard_speech and waited_frames >= max_wait_frames:
            return np.array([], dtype=np.int16)

        if heard_speech and len(frames) >= min_blocks and silent_blocks >= silence_limit:
            break

    if not heard_speech:
        return np.array([], dtype=np.int16)

    play_cue(settings.done_cue_hz, settings.cue_ms, settings.audible_cues)
    audio = np.concatenate(frames) if frames else np.array([], dtype=np.int16)
    return _trim_silence(audio, speech_threshold, settings.pre_roll_seconds)


def _listen_once(stream, settings: VoiceSettings, speech_threshold: int) -> str:
    command_audio = record_command(stream, settings, speech_threshold)
    if command_audio.size == 0:
        return ""

    console.print("[dim]Transcribing...[/dim]")
    return transcribe_audio(command_audio)


def _handle_command(session: AssistantSession, speaker: Speaker, command: str) -> Speaker:
    if not command:
        response = "I did not catch that."
    else:
        console.print(f"[bold green]You:[/bold green] {command}")
        console.print("[dim]Thinking...[/dim]")
        response = session.process_text(command)

    console.print(f"[bold blue]Jarvis:[/bold blue] {response}\n")
    if session.should_speak:
        speaker = Speaker()
        speak(speaker, response)
    return speaker


def _run_conversation_session(stream, settings: VoiceSettings, speech_threshold: int, speaker: Speaker) -> Speaker:
    session = AssistantSession(source="voice")
    console.print(
        f"[dim]{session.mode.label} session active. "
        f"Say 'stop listening' when you are done.[/dim]"
    )
    last_heard = time.monotonic()
    turns = 0

    while turns < session.mode.session_max_turns:
        if time.monotonic() - last_heard > session.mode.session_idle_timeout_seconds:
            console.print("[dim]Conversation session timed out.[/dim]\n")
            break

        command = _listen_once(stream, settings, speech_threshold)
        if not command:
            console.print("[dim]No follow-up heard.[/dim]\n")
            break

        last_heard = time.monotonic()
        turns += 1
        stop_after_response = session.is_stop_phrase(command)
        speaker = _handle_command(session, speaker, command)
        if stop_after_response:
            break

    return speaker


def run_voice_loop(mode_name: str | None = None) -> None:
    """Start the always-on wake-word loop."""
    sd, Model, oww_utils = _require_audio_stack()
    settings = VoiceSettings.from_config()
    speaker = Speaker()
    session = AssistantSession(mode_name=mode_name, source="voice")

    if session.mode.name == "push_to_talk":
        run_push_to_talk_loop(mode_name=session.mode.name)
        return

    console.print("[bold cyan]Jarvis voice mode[/bold cyan]")
    console.print(f"Mode: [bold]{session.mode.label}[/bold]. {session.mode.description}")
    console.print(f"Wake word: [bold]{settings.wake_word}[/bold]. Press Ctrl+C to stop.")
    console.print(f"[dim]TTS provider: {speaker.provider_status}[/dim]")

    try:
        oww_utils.download_models()
    except Exception as exc:
        console.print(f"[yellow]Could not download/update wake-word models:[/yellow] {exc}")

    model = Model(
        wakeword_models=[settings.wake_word],
        vad_threshold=settings.vad_threshold,
        inference_framework=settings.wake_inference_framework,
    )
    frame_size = int(SAMPLE_RATE * 0.08)
    last_activation = 0.0

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=frame_size) as stream:
            noise_floor = calibrate_noise_floor(stream)
            speech_threshold = effective_speech_threshold(settings, noise_floor)
            console.print(
                f"[dim]Mic noise floor: {noise_floor:.0f}. Speech threshold: {speech_threshold}.[/dim]"
            )
            known_models_printed = False
            while True:
                frame, _ = stream.read(frame_size)
                prediction = model.predict(frame.reshape(-1))

                if not known_models_printed:
                    names = ", ".join(_model_names(prediction))
                    if names:
                        console.print(f"[dim]Loaded wake models: {names}[/dim]")
                    known_models_printed = True

                score = _wake_score(prediction, settings.wake_word)
                now = time.monotonic()
                if score < settings.wake_threshold or now - last_activation < settings.cooldown_seconds:
                    continue

                last_activation = now
                console.print(f"[green]Wake word detected[/green] ({score:.2f})")
                session.refresh_mode()
                if settings.prompt_after_wake:
                    speak(speaker, settings.wake_response)
                    if settings.listen_delay_seconds > 0:
                        time.sleep(settings.listen_delay_seconds)

                if session.mode.continuous_session:
                    speaker = _run_conversation_session(stream, settings, speech_threshold, speaker)
                else:
                    command = _listen_once(stream, settings, speech_threshold)
                    if not command:
                        console.print("[dim]No command heard.[/dim]\n")
                        continue
                    speaker = _handle_command(session, speaker, command)
    except KeyboardInterrupt:
        console.print("\n[bold cyan]Jarvis voice mode stopped.[/bold cyan]")


def run_push_to_talk_loop(mode_name: str | None = None) -> None:
    """Terminal-friendly push-to-talk mode until a real tray hotkey exists."""
    sd, _, _ = _require_audio_stack()
    settings = VoiceSettings.from_config()
    speaker = Speaker()
    session = AssistantSession(mode_name=mode_name or "push_to_talk", source="push_to_talk")
    frame_size = int(SAMPLE_RATE * 0.08)

    console.print("[bold cyan]Jarvis push-to-talk mode[/bold cyan]")
    console.print("Press Enter to listen. Type Ctrl+C to stop.\n")

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=frame_size) as stream:
            noise_floor = calibrate_noise_floor(stream)
            speech_threshold = effective_speech_threshold(settings, noise_floor)
            console.print(
                f"[dim]Mic noise floor: {noise_floor:.0f}. Speech threshold: {speech_threshold}.[/dim]"
            )
            while True:
                console.input("[bold green]Push to talk:[/bold green] ")
                command = _listen_once(stream, settings, speech_threshold)
                speaker = _handle_command(session, speaker, command)
    except KeyboardInterrupt:
        console.print("\n[bold cyan]Jarvis push-to-talk mode stopped.[/bold cyan]")


def run_listen_test() -> None:
    """Record one dictation-style utterance and print the transcription."""
    sd, _, _ = _require_audio_stack()
    settings = VoiceSettings.from_config()
    frame_size = int(SAMPLE_RATE * 0.08)

    console.print("[bold cyan]Jarvis listen test[/bold cyan]")
    console.print("Speak after the beep. This will not run any action.\n")

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=frame_size) as stream:
            noise_floor = calibrate_noise_floor(stream)
            speech_threshold = effective_speech_threshold(settings, noise_floor)
            console.print(
                f"[dim]Mic noise floor: {noise_floor:.0f}. Speech threshold: {speech_threshold}.[/dim]"
            )
            audio = record_command(stream, settings, speech_threshold)
            if audio.size == 0:
                console.print("[yellow]No speech detected.[/yellow]")
                return

            console.print("[dim]Transcribing...[/dim]")
            text = transcribe_audio(audio)
            console.print(f"[bold green]Transcript:[/bold green] {text or '(empty)'}")
    except KeyboardInterrupt:
        console.print("\n[bold cyan]Jarvis listen test stopped.[/bold cyan]")
