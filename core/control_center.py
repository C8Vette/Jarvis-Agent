from __future__ import annotations

import importlib.util
import json
import mimetypes
import os
import secrets
import shutil
import subprocess
import sys
import traceback
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values

from rich.console import Console

from core.actions import ACTION_REGISTRY
from core.config import (
    ROOT,
    load_device_config,
    load_permissions,
    save_device_config,
    save_permissions,
)
from core.modes import merge_modes_config, mode_options
from skills.dashboard import dashboard_state

console = Console()

UI_ROOT = ROOT / "ui" / "control_center"
HOST = "127.0.0.1"
CONTROL_LOG = ROOT / "data" / "logs" / "control-center.log"


def run_control_center(port: int = 8765) -> None:
    server = None
    try:
        token = secrets.token_urlsafe(24)
        server = ThreadingHTTPServer((HOST, port), _handler(token))
        _log(f"started http://{HOST}:{port}")
        _print("[bold cyan]Jarvis Control Center[/bold cyan]")
        _print(f"Open [bold]http://{HOST}:{port}[/bold]")
        _print("Press Ctrl+C to stop.\n")
        server.serve_forever()
    except KeyboardInterrupt:
        _print("\n[bold cyan]Control Center stopped.[/bold cyan]")
    except Exception:
        _log(traceback.format_exc())
        raise
    finally:
        if server:
            server.server_close()


def _print(message: str) -> None:
    try:
        console.print(message)
    except Exception:
        _log(f"console print failed: {message}")


def _log(message: str) -> None:
    CONTROL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with CONTROL_LOG.open("a", encoding="utf-8") as handle:
        handle.write(message.rstrip() + "\n")


def _handler(token: str):
    class ControlCenterHandler(BaseHTTPRequestHandler):
        server_version = "JarvisControlCenter/0.1"

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/state":
                self._send_json(_state())
                return
            if parsed.path == "/api/dashboard":
                self._send_json(dashboard_state())
                return
            if parsed.path == "/api/system":
                self._send_json(_system_status())
                return
            if parsed.path == "/api/token":
                self._send_json({"token": token})
                return

            self._serve_static(parsed.path)

        def do_POST(self) -> None:
            if self.headers.get("X-Jarvis-Control-Token") != token:
                self._send_json({"error": "Invalid control token."}, status=403)
                return

            parsed = urlparse(self.path)
            try:
                payload = self._read_json()
                if parsed.path == "/api/device":
                    self._save_device(payload)
                    return
                if parsed.path == "/api/permissions":
                    self._save_permissions(payload)
                    return
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return

            self._send_json({"error": "Not found."}, status=404)

        def log_message(self, format: str, *args) -> None:
            return

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise ValueError("Request body must be valid JSON.") from exc
            if not isinstance(data, dict):
                raise ValueError("Request body must be a JSON object.")
            return data

        def _save_device(self, payload: dict) -> None:
            current = load_device_config()
            updated = _merge_device_config(current, payload)
            save_device_config(updated)
            self._send_json({"ok": True, "device": updated})

        def _save_permissions(self, payload: dict) -> None:
            updated = _sanitize_permissions(payload)
            save_permissions(updated)
            self._send_json({"ok": True, "permissions": updated})

        def _serve_static(self, request_path: str) -> None:
            relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
            path = (UI_ROOT / relative).resolve()
            try:
                path.relative_to(UI_ROOT.resolve())
            except ValueError:
                self.send_error(404)
                return

            if not path.exists() or not path.is_file():
                self.send_error(404)
                return

            content = path.read_bytes()
            content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            if path.name == "index.html":
                content = content.replace(b"__JARVIS_CONTROL_TOKEN__", token.encode("utf-8"))

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)

        def _send_json(self, data: dict, status: int = 200) -> None:
            content = json.dumps(data, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)

    return ControlCenterHandler


def _state() -> dict:
    return {
        "device": load_device_config(),
        "permissions": load_permissions(),
        "dashboard": dashboard_state(),
        "system": _system_status(),
        "activity": _recent_activity(),
        "actions": {
            name: asdict(definition)
            for name, definition in sorted(ACTION_REGISTRY.items())
        },
        "mode_options": mode_options(),
    }

def _system_status() -> dict:
    return {
        "root": str(ROOT),
        "python": _python_status(),
        "env": _env_status(),
        "tts": _tts_status(),
        "processes": _process_status(),
        "git": _git_status(),
        "logs": _log_status(),
    }


def _python_status() -> dict:
    return {
        "executable": sys.executable,
        "version": sys.version.split()[0],
        "openai_package": importlib.util.find_spec("openai") is not None,
        "sounddevice_package": importlib.util.find_spec("sounddevice") is not None,
        "openwakeword_package": importlib.util.find_spec("openwakeword") is not None,
        "pyttsx3_package": importlib.util.find_spec("pyttsx3") is not None,
    }


def _env_status() -> dict:
    env_path = ROOT / ".env"
    values = dotenv_values(env_path) if env_path.exists() else {}
    keys = [
        "OPENAI_API_KEY",
        "JARVIS_MODEL",
        "JARVIS_CHAT_MODEL",
        "ELEVENLABS_API_KEY",
        "ELEVENLABS_VOICE_ID",
        "ELEVENLABS_ACTIVE_VOICE",
    ]
    return {
        "path": str(env_path),
        "exists": env_path.exists(),
        "keys": {
            key: bool(os.getenv(key) or values.get(key))
            for key in keys
        },
    }


def _tts_status() -> dict:
    try:
        from core.speech import Speaker, TTSSettings

        settings = TTSSettings.from_config()
        speaker = Speaker(settings)
        return {
            "enabled": settings.enabled,
            "provider": settings.provider,
            "fallback_provider": settings.fallback_provider,
            "active_voice": settings.elevenlabs_active_voice,
            "voice_id_configured": bool(settings.elevenlabs_voice_id),
            "status": speaker.provider_status,
        }
    except Exception as exc:
        return {"error": str(exc)}


def _process_status() -> dict:
    script = (
        "Get-CimInstance Win32_Process -Filter \"name = 'python.exe'\" | "
        "Where-Object { $_.CommandLine -like '*jarvis-agent*' } | "
        "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception as exc:
        return {"available": False, "error": str(exc), "items": []}

    if result.returncode != 0:
        return {
            "available": False,
            "error": (result.stderr or result.stdout).strip(),
            "items": [],
        }

    raw = result.stdout.strip()
    if not raw:
        return {"available": True, "items": []}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"available": False, "error": raw, "items": []}

    items = parsed if isinstance(parsed, list) else [parsed]
    return {
        "available": True,
        "items": [
            {
                "pid": item.get("ProcessId"),
                "command": str(item.get("CommandLine", "")),
            }
            for item in items
            if isinstance(item, dict)
        ],
    }


def _git_status() -> dict:
    git = shutil.which("git")
    if not git:
        portable = Path.home() / "PortableGit" / "cmd" / "git.exe"
        if portable.exists():
            git = str(portable)
    if not git:
        return {"available": False, "error": "git.exe not found"}

    def run_git(*args: str) -> dict:
        try:
            result = subprocess.run(
                [git, "-C", str(ROOT), *args],
                capture_output=True,
                text=True,
                timeout=8,
            )
        except Exception as exc:
            return {"ok": False, "output": str(exc)}
        output = (result.stdout or result.stderr).strip()
        return {"ok": result.returncode == 0, "output": output}

    return {
        "available": True,
        "status": run_git("status", "-sb"),
        "head": run_git("log", "-1", "--oneline"),
        "remote": run_git("remote", "-v"),
    }


def _log_status(limit: int = 8) -> list[dict]:
    log_dir = ROOT / "data" / "logs"
    if not log_dir.exists():
        return []

    logs = []
    for path in sorted(log_dir.glob("*.log")):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
            stat = path.stat()
        except OSError:
            continue
        logs.append(
            {
                "name": path.name,
                "size": stat.st_size,
                "modified": int(stat.st_mtime),
                "tail": lines,
            }
        )
    return logs

def _recent_activity(limit: int = 12) -> list[dict]:
    audit_path = ROOT / "data" / "audit.log"
    if not audit_path.exists():
        return []

    try:
        lines = audit_path.read_text(encoding="utf-8").splitlines()[-limit:]
    except OSError:
        return []

    events = []
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(
                {
                    "timestamp": str(event.get("timestamp", "")),
                    "action": str(event.get("action", "")),
                    "status": str(event.get("status", "")),
                    "command": str(event.get("command", "")),
                    "message": str(event.get("message", "")),
                }
            )
    return events


def _merge_device_config(current: dict, payload: dict) -> dict:
    updated = dict(current)
    for key in ("device_name",):
        if key in payload:
            updated[key] = str(payload[key]).strip()

    for key in ("allowed_folders",):
        if key in payload:
            updated[key] = _clean_string_list(payload[key])

    for key in ("apps", "websites"):
        if key in payload:
            updated[key] = _clean_string_map(payload[key])

    if "voice" in payload:
        updated["voice"] = _merge_section(updated.get("voice", {}), payload["voice"], _VOICE_SCHEMA)

    if "assistant_modes" in payload:
        updated["assistant_modes"] = merge_modes_config(payload["assistant_modes"])

    if "tts" in payload:
        tts = dict(updated.get("tts", {}))
        incoming_tts = payload["tts"] if isinstance(payload["tts"], dict) else {}
        tts = _merge_section(tts, incoming_tts, _TTS_SCHEMA)
        if "local" in incoming_tts:
            tts["local"] = _merge_section(tts.get("local", {}), incoming_tts["local"], _LOCAL_TTS_SCHEMA)
        if "elevenlabs" in incoming_tts:
            tts["elevenlabs"] = _merge_section(
                tts.get("elevenlabs", {}),
                incoming_tts["elevenlabs"],
                _ELEVENLABS_SCHEMA,
            )
            incoming_elevenlabs = incoming_tts["elevenlabs"]
            if isinstance(incoming_elevenlabs, dict) and "profiles" in incoming_elevenlabs:
                profiles = incoming_elevenlabs.get("profiles", {})
                tts["elevenlabs"]["profiles"] = _clean_voice_profiles(profiles)
            active_voice = str(tts["elevenlabs"].get("active_voice", "")).strip()
            profiles = tts["elevenlabs"].get("profiles", {})
            if active_voice and isinstance(profiles, dict):
                profile = profiles.get(active_voice, {})
                if isinstance(profile, dict) and profile.get("voice_id"):
                    tts["elevenlabs"]["voice_id"] = profile["voice_id"]
        updated["tts"] = tts

    return updated


def _merge_section(current: dict, incoming: object, schema: dict[str, type]) -> dict:
    if not isinstance(incoming, dict):
        return current

    updated = dict(current)
    for key, expected_type in schema.items():
        if key not in incoming:
            continue
        value = incoming[key]
        if expected_type is bool:
            updated[key] = bool(value)
        elif expected_type is int:
            updated[key] = int(value)
        elif expected_type is float:
            updated[key] = float(value)
        else:
            updated[key] = str(value).strip()
    return updated


def _clean_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _clean_string_map(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    cleaned = {}
    for key, item in value.items():
        name = str(key).strip().lower()
        target = str(item).strip()
        if name and target:
            cleaned[name] = target
    return cleaned


def _clean_voice_profiles(value: object) -> dict[str, dict[str, str]]:
    if not isinstance(value, dict):
        return {}
    cleaned = {}
    for key, item in value.items():
        name = str(key).strip()
        if not name:
            continue
        if isinstance(item, dict):
            voice_id = str(item.get("voice_id", "")).strip()
            description = str(item.get("description", "")).strip()
        else:
            voice_id = str(item).strip()
            description = ""
        if voice_id:
            cleaned[name] = {"voice_id": voice_id}
            if description:
                cleaned[name]["description"] = description
    return cleaned


def _sanitize_permissions(payload: dict) -> dict:
    valid_actions = set(ACTION_REGISTRY)
    result = {
        "auto_allow": [],
        "require_confirmation": [],
        "blocked": [],
    }
    assigned = set()

    for bucket in result:
        raw_items = payload.get(bucket, [])
        if not isinstance(raw_items, list):
            continue
        for item in raw_items:
            action = str(item).strip()
            if action in valid_actions and action not in assigned:
                result[bucket].append(action)
                assigned.add(action)

    for action, definition in ACTION_REGISTRY.items():
        if action in assigned:
            continue
        result[definition.default_policy].append(action)

    return result


_VOICE_SCHEMA = {
    "wake_word": str,
    "wake_threshold": float,
    "wake_inference_framework": str,
    "vad_threshold": float,
    "command_seconds": float,
    "start_timeout_seconds": float,
    "silence_seconds": float,
    "min_command_seconds": float,
    "pre_roll_seconds": float,
    "speech_rms_threshold": int,
    "speech_rms_multiplier": float,
    "min_speech_rms_threshold": int,
    "prompt_after_wake": bool,
    "wake_response": str,
    "listen_delay_seconds": float,
    "audible_cues": bool,
    "listen_cue_hz": int,
    "done_cue_hz": int,
    "cue_ms": int,
    "cooldown_seconds": float,
}

_TTS_SCHEMA = {
    "enabled": bool,
    "provider": str,
    "fallback_provider": str,
}

_LOCAL_TTS_SCHEMA = {
    "rate": int,
}

_ELEVENLABS_SCHEMA = {
    "api_key_env": str,
    "active_voice": str,
    "voice_id": str,
    "model_id": str,
    "output_format": str,
    "stability": float,
    "similarity_boost": float,
}
