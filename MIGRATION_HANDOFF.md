# Jarvis Agent Migration Handoff

Last updated: 2026-07-17

This document is the project handoff for moving Jarvis Agent to a new Windows computer or reopening the project in a fresh Codex task. It is intentionally safe to commit: it should not contain API keys, OAuth tokens, virtual environments, logs, or private local data.

## Source Of Truth

The code source of truth is the GitHub repository:

```text
https://github.com/C8Vette/Jarvis-Agent.git
```

Codex chat history is useful context, but it is not part of the repo. If the original Codex task does not appear on the new computer, clone the repo and use this file plus `README.md` as the handoff context.

## Current Product Direction

Jarvis Agent is a local Windows voice assistant that is being built toward a secure, marketable desktop assistant. The near-term goal is a reliable personal assistant with:

- Wake-word voice control
- Command and conversation modes
- Local task, reminder, and project memory
- A daily operating dashboard
- Secure action routing and audit logging
- Configurable app/site/browser actions
- Optional premium TTS with local fallback
- A Control Center UI for tuning settings
- A background runner so Jarvis does not need a visible terminal

The long-term goal is a polished desktop application with a proper frontend, tray/background process, richer integrations such as Gmail/Moodle/calendar, and eventually a backend/proxy model for paid API features.

## What Is In Git

These should be available after cloning:

- `main.py`: CLI entry point for typed, voice, TTS test, Gmail setup, listen test, and Control Center modes
- `core/`: shared runtime, assistant logic, action registry, safety checks, routing, memory, speech, TTS, conversation, config, and audit logging
- `skills/`: safe capability adapters such as browser actions, daily brief, dashboard, tasks, reminders, projects, file actions, settings, and Gmail scaffolding
- `config/`: default tracked user/device/permission configuration
- `ui/control_center/`: local browser Control Center frontend
- `scripts/`: Windows background runner, stop scripts, and desktop shortcut installer
- `requirements*.txt`: base, voice, and optional integration dependencies
- `README.md`: current usage and architecture notes

## What Is Local Only

These are intentionally ignored by Git and must be recreated or copied manually:

- `.env`: API keys and secrets
- `.venv/`: Python virtual environment
- `data/`: local memory, logs, OAuth credentials, OAuth tokens, and audit logs
- `data/tasks.yaml`: local tasks
- `data/reminders.yaml`: local reminders
- `data/projects.yaml`: local projects
- `data/google/credentials.json`: Gmail OAuth client file
- `data/google/token.json`: Gmail OAuth token

Never commit `.env`, `.venv/`, OAuth tokens, logs, or personal data exports.

## New Computer Setup

Clone the project:

```powershell
git clone https://github.com/C8Vette/Jarvis-Agent.git
cd Jarvis-Agent
```

Create and populate a fresh virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-voice.txt
```

Install optional integration dependencies only when needed:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-integrations.txt
```

Create `.env` from `.env.example` and add local secrets:

```env
OPENAI_API_KEY=
JARVIS_MODEL=
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
```

The exact values should come from the user's provider dashboards. Do not place API keys in `config/device.yaml`.

## Local Data Migration

If the user wants existing tasks, projects, and reminders on the new computer, copy these files from the old machine into the new repo:

```text
data/tasks.yaml
data/projects.yaml
data/reminders.yaml
```

If Gmail has already been connected and the user wants to preserve that local OAuth session, copy `data/google/` carefully. If in doubt, reconnect Gmail on the new computer instead of copying tokens.

## Shortcut And Background Runner

After dependencies are installed, recreate Windows shortcuts:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_jarvis_shortcuts.ps1
```

Start both Control Center and voice mode in the background:

```powershell
.\scripts\start_jarvis_background.ps1
```

Stop the background runner:

```powershell
.\scripts\stop_jarvis_background.ps1
```

The current Control Center URL is:

```text
http://127.0.0.1:8765
```

This localhost server runs on the user's own computer and does not cost money by itself.

## Current Voice Setup

Voice mode currently uses `openWakeWord` with the `hey jarvis` wake word. The speech loop was redesigned so it listens more naturally after wake activation and avoids cutting off longer commands too early.

Current important settings live in `config/device.yaml`:

- Wake word: `hey jarvis`
- Wake backend: `openWakeWord` using ONNX
- TTS provider: ElevenLabs, with local fallback
- Current ElevenLabs profile: `Patrick`
- Assistant mode: `conversation`

The user previously discovered that the Windows microphone input level was extremely low. If transcription gets bad again, check Windows microphone volume/input level before changing code.

## Assistant Modes

Jarvis has shared assistant logic across modes so improvements do not need to be copied four times.

- `command`: wake word, one command, one response
- `conversation`: wake word opens a short multi-turn session with follow-up context
- `push-to-talk`: deliberate voice input mode
- `assist`: lower-cost deterministic mode that avoids the LLM router

Mode switching should work through typed or spoken commands such as:

```text
switch to conversation mode
switch to command mode
switch to assist mode
what mode are you in
```

The conversation mode has basic follow-up memory. For example, if Jarvis asks for a task description, the next user response should be treated as the missing description instead of a brand-new command.

## Current Capability Map

Jarvis can currently:

- Add, list, and complete tasks
- Add, list, and complete reminders
- Add and update projects
- Generate a daily brief
- Show dashboard data in the Control Center
- Open configured apps and sites
- Search the web or YouTube with the Windows default browser
- Search allowed local folders
- Open files/folders under allowed paths
- Switch assistant modes
- Switch TTS provider and ElevenLabs voice profiles
- Run read-only Gmail scaffolding once Google OAuth is configured

Every action should go through the secure action registry in `core/actions.py`, safety policy in `config/permissions.yaml`, and audit logging in `core/audit.py`.

## Security Model

The important safety rule is: Jarvis should not freely run arbitrary computer actions without going through the action registry.

Actions are categorized in `config/permissions.yaml`:

- `auto_allow`: safe actions Jarvis can run immediately
- `require_confirmation`: actions that need explicit user approval
- `blocked`: actions Jarvis should refuse

Current examples:

- Opening apps/sites and reading local task memory are generally allowed
- Terminal commands, file deletion, email sending, package installation, and system setting changes require confirmation or should remain constrained
- Browser actions should use the Windows default browser rather than hard-coding Opera GX

## TTS Notes

ElevenLabs is optional and should fail gracefully. If ElevenLabs runs out of credits, rejects a voice, or returns a payment/API error, Jarvis should fall back to the configured local provider instead of repeatedly hammering the ElevenLabs API.

Voice profile IDs may be stored in `config/device.yaml`; API keys must stay in `.env`.

Useful voice commands:

```text
use ElevenLabs voice
use Windows voice
use local voice
mute Jarvis
unmute Jarvis
voice status
set voice to Patrick
```

## Integration Roadmap

Likely next development steps:

1. Polish the frontend into a real desktop-feeling app shell with listening/status animation.
2. Improve packaging so Jarvis can install and run like normal Windows software.
3. Add Gmail read-only digest once Google Cloud credentials are ready.
4. Add Moodle assignment/course integration.
5. Add calendar integration.
6. Build richer daily planning: open tasks, due dates, projects, reminders, school sources, and one recommended focus.
7. Add a backend/proxy model for commercial API features so end users do not need to manage provider keys.
8. Add a proper tray app with global push-to-talk and startup behavior.

## Handoff Prompt For A New Codex Task

If opening this project in a fresh Codex task, paste this:

```text
We are working on Jarvis Agent, a local Windows voice assistant in this repo. Please read MIGRATION_HANDOFF.md and README.md first. The project already has voice command/conversation modes, a Control Center, secure action registry, audit logging, configurable app/site/browser actions, local tasks/reminders/projects, daily brief/dashboard, ElevenLabs optional TTS with local fallback, and background runner scripts. Keep secrets out of Git. Use GitHub as source of truth, and treat data/, .env, and .venv/ as local-only.
```
