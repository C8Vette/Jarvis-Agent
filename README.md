# Jarvis Desktop Agent

Local Windows assistant for opening apps/sites, searching allowed folders, and building toward a voice-first personal workflow assistant.

## Current capabilities

- Typed command loop: `python main.py`
- Voice command loop: `python main.py --voice`
- Assistant modes: command, conversation, push-to-talk, and assist
- Local Control Center: `python main.py --control-center`
- Deterministic routing for common local actions before using the LLM router
- Action registry in `core/actions.py`
- Safety policy in `config/permissions.yaml`
- Local audit log at `data/audit.log`
- Device-specific apps, websites, and allowed folders in `config/device.yaml`
- Browser URLs open with the Windows default browser
- Personal routine and school/project context in `config/user.yaml`

## Voice stack

Voice mode uses `openWakeWord` by default because it is open source and includes a pre-trained `hey jarvis` model. Picovoice Porcupine is a good future optional backend, especially if you want commercial support or a custom wake word, but it requires an access key.

Install the base dependencies from `requirements.txt`, then install voice extras:

```powershell
pip install -r requirements-voice.txt
```

Then run:

```powershell
python main.py --voice
```

Run a specific mode without changing the saved default:

```powershell
python main.py --voice --mode conversation
python main.py --voice --mode assist
python main.py --voice --mode push-to-talk
```

Voice tuning lives in `config/device.yaml` under `voice:`. Environment variables with the same meaning can still be used as temporary overrides while testing:

- `JARVIS_WAKE_WORD`: defaults to `hey jarvis`
- `JARVIS_WAKE_THRESHOLD`: defaults to `0.8`
- `JARVIS_WAKE_INFERENCE_FRAMEWORK`: defaults to `onnx`
- `JARVIS_VAD_THRESHOLD`: defaults to `0.3`
- `JARVIS_COMMAND_SECONDS`: maximum command speech window after wake-up, defaults to `45.0`
- `JARVIS_START_TIMEOUT_SECONDS`: how long Jarvis waits for speech after wake-up, defaults to `8.0`
- `JARVIS_SILENCE_SECONDS`: stop recording after this much silence once speech started, defaults to `3.0`
- `JARVIS_PRE_ROLL_SECONDS`: include this much audio from just before detected speech, defaults to `0.7`
- `JARVIS_SPEECH_RMS_THRESHOLD`: fixed microphone speech threshold; `0` means auto-calibrate, defaults to `0`
- `JARVIS_SPEECH_RMS_MULTIPLIER`: auto threshold multiplier over room noise, defaults to `2.4`
- `JARVIS_MIN_SPEECH_RMS_THRESHOLD`: minimum auto threshold, defaults to `120`
- `JARVIS_PROMPT_AFTER_WAKE`: say the configured wake response after wake word, defaults to `false`
- `JARVIS_WAKE_RESPONSE`: spoken wake acknowledgement, defaults to `Yes?`
- `JARVIS_LISTEN_DELAY_SECONDS`: pause after the spoken wake prompt before recording, defaults to `0.2`
- `JARVIS_AUDIBLE_CUES`: play short listen/done beeps, defaults to `true`
- `JARVIS_TRANSCRIBE_MODEL`: defaults to `whisper-1`

TTS tuning lives in `config/device.yaml` under `tts:`. Windows speech is the default stable provider. ElevenLabs is available as an optional provider when the selected voice is API-eligible.

- `JARVIS_TTS_ENABLED`: enable or disable spoken responses
- `JARVIS_TTS_PROVIDER`: `windows`, `local`, `pyttsx3`, `elevenlabs`, or `none`
- `JARVIS_TTS_RATE`: local `pyttsx3` speech rate
- `ELEVENLABS_API_KEY`: API key for ElevenLabs
- `ELEVENLABS_VOICE_ID`: ElevenLabs voice ID
- `ELEVENLABS_MODEL_ID`: ElevenLabs model, defaults to `eleven_multilingual_v2`

Put ElevenLabs secrets in `.env`, not in `config/device.yaml`:

```env
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
```

Test configured TTS without starting voice mode:

```powershell
python main.py --say "Good morning, Ethan."
```

Test listening/transcription without wake word or actions:

```powershell
python main.py --listen-test
```

## Gmail Integration

Gmail support is read-only for now. Jarvis uses the `gmail.readonly` OAuth scope and stores local OAuth files under `data/google/`, which is ignored by Git.

Install optional integration dependencies:

```powershell
pip install -r requirements-integrations.txt
```

Setup:

1. In Google Cloud, enable the Gmail API.
2. Configure OAuth consent for a desktop app.
3. Download the OAuth client JSON.
4. Save it as `data/google/credentials.json`.
5. Run:

```powershell
python main.py --gmail-connect
```

Useful commands:

- `gmail status`
- `check gmail`
- `gmail digest`
- `read important emails`

## Control Center

Start the local settings UI:

```powershell
python main.py --control-center
```

Then open:

```text
http://127.0.0.1:8765
```

The Control Center edits `config/device.yaml` and `config/permissions.yaml`. It currently covers the daily operating dashboard, voice tuning, TTS provider settings, ElevenLabs voice profiles, configured apps/sites/folders, and action policies.

## Assistant Modes

All modes call the same shared assistant runtime in `core/assistant.py`, then route through the same memory, safety, audit, and skill layers. That keeps improvements to command understanding from being copied into four separate places.

- `command`: the stable default. Wake word, one command, one response.
- `conversation`: wake word opens a short multi-turn session for follow-ups, normal questions, and lightweight chat.
- `push-to-talk`: terminal-triggered starter mode for deliberate voice input. A proper global hotkey belongs in the future tray app.
- `assist`: lower-cost mode that skips the LLM router and only uses deterministic local skills.

You can switch modes from the Control Center or by saying/typing:

- `switch to conversation mode`
- `switch to command mode`
- `switch to assist mode`
- `what mode are you in`

Realtime speech is represented in the mode config as a future backend/proxy integration. It stays disabled until the app has a proper backend that can control cost, issue short-lived session tokens, and keep provider API keys off customer machines.

Under the hood, mode behavior starts in `core/intent.py`. The intent layer decides whether a turn is a command, chat, small talk, or a stop phrase. Commands go through the secure router/action registry. Conversation turns go through `core/chat.py`, which uses local replies first and can use the configured OpenAI chat model when available.

## Background Runner

Jarvis can run without keeping a terminal open.

Start both Control Center and voice mode:

```powershell
.\scripts\start_jarvis_background.ps1
```

Stop both:

```powershell
.\scripts\stop_jarvis_background.ps1
```

Install Desktop shortcuts:

```powershell
.\scripts\install_jarvis_shortcuts.ps1
```

Logs are written to `data/logs/`.

## Skill Architecture

Files in `skills/` are capability adapters, not the whole intelligence of Jarvis. A skill should do one concrete kind of work, such as opening websites, searching files, or producing a daily brief. The router decides which action to run, the safety layer checks whether it is allowed, and the audit layer records what happened.

As Jarvis gets smarter, the goal is not to hard-code every possible sentence. The goal is to add safe, reusable tools that an LLM router or future planner can choose from.

## Local Memory

Jarvis stores local task memory in `data/tasks.yaml`. This file is intentionally local and ignored by Git.
Jarvis stores local project memory in `data/projects.yaml`, also ignored by Git.
Jarvis stores local reminders in `data/reminders.yaml`, also ignored by Git.

Useful commands:

- `add task review Moodle due tomorrow`
- `can you add another task? I have an essay due on July 7th` followed by `CSC 7335 research paper`
- `remind me to submit the lab due 2026-07-10`
- `what are my tasks`
- `complete task 1`
- `add reminder check Moodle due tomorrow`
- `what are my reminders`
- `complete reminder 1`
- `add project CSC 7335 research paper due July 7th`
- `set next action for CSC 7335 research paper to outline the introduction`
- `set project CSC 7335 research paper status to active`
- `what are my projects`
- `daily brief`

The daily brief merges routine config, school sources, active projects, next actions, and open tasks.

The Control Center Dashboard shows open task counts, due dates, active projects, school sources, reminders, the spoken brief, and one recommended focus.

Jarvis also keeps one short pending conversation turn in memory. If he asks for a task description, your next response is treated as that description instead of a fresh command. Say `cancel` or `never mind` to clear the pending request.

## Voice Provider Commands

These commands update `config/device.yaml` so they are available to the current voice session and future runs:

- `use ElevenLabs voice`
- `use Windows voice`
- `use local voice`
- `mute Jarvis`
- `unmute Jarvis`
- `voice status`
- `set voice to <configured ElevenLabs profile name>`

ElevenLabs voice profiles live in `config/device.yaml` under `tts.elevenlabs.profiles`. Store only voice IDs there; keep the API key in `.env`.

## Action Safety

Every action should be registered in `core/actions.py`, then enabled in `config/permissions.yaml` as one of:

- `auto_allow`: safe actions Jarvis can run immediately
- `require_confirmation`: actions Jarvis must ask before running
- `blocked`: actions Jarvis should refuse

All routed actions are logged as JSON lines in `data/audit.log`.

## Next robust-agent milestones

1. Add Moodle integration for assignments, due dates, and course announcements.
2. Add Gmail/email read-only digesting, with send actions requiring confirmation.
3. Add a morning brief that merges routine, Moodle, calendar, email, and active project state.
4. Add durable memory for projects and workflow advice.
5. Add a tray/background runner so voice mode can launch on startup.
