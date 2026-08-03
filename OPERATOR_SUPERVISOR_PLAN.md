# Operator / Supervisor Architecture

Last updated: 2026-08-03

This is the plan for moving Jarvis from a local command assistant toward an Iron Man-style autonomous workstation operator. The goal is not to make Jarvis reckless. The goal is to give Jarvis a controlled work loop with visibility, approvals, and hard stop boundaries.

## Product Goal

Jarvis should eventually be able to accept a project objective, break it into steps, use allowed local tools and coding agents, report progress, ask for approval before risky actions, and stop immediately when requested.

The dedicated machine makes this practical because it can run long-lived services, local models, local memory/search, browser automation, and background jobs without fighting the user's daily computer for resources.

## Core Components

1. Supervisor
   - Owns the job queue.
   - Tracks job status, current step, next check-in, risk level, and last activity.
   - Decides when Jarvis must ask Ethan before continuing.

2. Operator Jobs
   - Durable records in local memory.
   - Each job has an objective, status, notes, safety policy, and event log.
   - Jobs start as queued. Future versions can move them to running, waiting_for_approval, blocked, completed, or canceled.

3. Tool Adapters
   - Small, permissioned capabilities such as terminal execution, browser navigation, file edits, Git operations, Codex/Claude task interaction, and screenshots.
   - Every adapter must map to the action registry and safety policy.

4. State Inspector
   - Reads current system state: running processes, active repo, Git status, logs, browser page state, queued jobs, and recent actions.
   - Future versions can include screenshots and OCR when a visual agent needs to understand UI state.

5. Approval Gate
   - Blocks risky actions until approved.
   - Examples: terminal commands, package installation, deleting or moving files, sending messages/email, pushing Git branches, approving external agent requests, and changing system settings.

6. Check-In Loop
   - Jarvis should summarize what it is doing at regular intervals.
   - Jobs should have explicit check-in rules such as before_terminal, before_external_write, every_n_minutes, or when_blocked.

7. Kill Switch
   - A stop command must halt active jobs and prevent new actions.
   - Future tray UI should include a visible stop button.

## Safety Boundaries

Jarvis may eventually operate Claude, ChatGPT, Codex, browsers, and terminals, but it should never silently bypass the action registry. Any skill that touches the outside world or changes local state must be registered, policy-checked, and audit-logged.

Default policies:

- Read-only inspection: usually auto-allow.
- Local memory writes: usually auto-allow.
- Browser/app launching: auto-allow if configured.
- Terminal commands: require confirmation.
- Package installs: require confirmation.
- File writes outside explicit workspace: require confirmation.
- Deletes/moves: require confirmation or blocked by default.
- Sending external messages/email: require confirmation.
- Approving Claude/ChatGPT/Codex tool requests: require confirmation until a narrower allowlist exists.

## Phases

### Phase 1: Safe Job Queue

Implemented first. Jarvis can create, list, inspect, and cancel supervised operator jobs. No external execution yet.

### Phase 2: Dry-Run Planner

Jarvis proposes steps for a job, estimates risk, and asks for approval before running anything.

### Phase 3: Local Tool Execution

Jarvis can run approved local tools such as repo inspection, tests, and status checks. Terminal execution remains confirmation-gated.

### Phase 4: Browser/App State Inspection

Jarvis can inspect selected windows/pages, gather state, and report what it sees. Visual automation remains gated.

### Phase 5: Agent Delegation

Jarvis can create or manage tasks in Codex/Claude/ChatGPT through official APIs or controlled UI automation. It reports progress and asks before approving tool/terminal requests.

### Phase 6: Autonomous Work Sessions

Jarvis can run bounded work sessions on a project with scheduled check-ins, persistent logs, and strict stop behavior.

## First Safe Implementation

The first implementation adds local commands:

- `create operator job <objective>`
- `start supervised task <objective>`
- `operator status`
- `show operator jobs`
- `cancel operator job <id or text>`

These commands only manage local job records. They do not yet operate Claude, ChatGPT, Codex, a browser, or the terminal.

## Next Implementation After Phase 1

The next step should be a dry-run planner that takes a queued job and returns:

- proposed steps
- required tools
- risk level per step
- approval points
- expected check-ins

Only after that planner feels reliable should Jarvis execute even small local actions on behalf of a job.