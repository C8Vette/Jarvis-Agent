from rich.console import Console
from core.assistant import AssistantSession

console = Console()

def run_text_loop(mode_name: str | None = None):
    session = AssistantSession(mode_name=mode_name, source="text")
    console.print("[bold cyan]Jarvis Desktop Agent[/bold cyan]")
    console.print(f"Mode: [bold]{session.mode.label}[/bold]. {session.mode.description}")
    console.print("Type a command. Example: open email, open chrome, find resume")
    console.print("Type 'exit' to quit.\n")

    while True:
        command = console.input("[bold green]You:[/bold green] ")

        if command.lower().strip() in ["exit", "quit"]:
            console.print("[bold cyan]Jarvis shutting down.[/bold cyan]")
            break

        session.refresh_mode()
        result = session.process_text(command)
        console.print(f"[bold blue]Jarvis:[/bold blue] {result}\n")

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Jarvis Desktop Agent")
    parser.add_argument("--voice", action="store_true", help="Start wake-word voice mode")
    parser.add_argument(
        "--mode",
        choices=["command", "conversation", "push_to_talk", "push-to-talk", "assist"],
        help="Override the configured assistant mode for this run",
    )
    parser.add_argument("--listen-test", action="store_true", help="Record and transcribe one utterance without routing")
    parser.add_argument("--say", help="Speak a phrase with the configured TTS provider, then exit")
    parser.add_argument("--control-center", action="store_true", help="Start the local Jarvis Control Center")
    parser.add_argument("--port", type=int, default=8765, help="Control Center port")
    parser.add_argument("--gmail-connect", action="store_true", help="Authorize Gmail read-only access")
    args = parser.parse_args()

    if args.say:
        from core.speech import Speaker

        speaker = Speaker()
        console.print(f"[dim]TTS provider: {speaker.provider_status}[/dim]")
        if speaker.say(args.say):
            console.print(f"[green]TTS spoke via {speaker.last_provider_used or speaker.provider_name}.[/green]")
            if speaker.last_error:
                console.print(f"[yellow]Primary TTS warning:[/yellow] {speaker.last_error}")
        else:
            console.print(f"[yellow]TTS failed:[/yellow] {speaker.last_error or speaker.provider_status}")
        return

    if args.voice:
        from core.voice import run_voice_loop

        run_voice_loop(mode_name=args.mode)
        return

    if args.listen_test:
        from core.voice import run_listen_test

        run_listen_test()
        return

    if args.control_center:
        from core.control_center import run_control_center

        run_control_center(port=args.port)
        return

    if args.gmail_connect:
        from skills.gmail import gmail_connect

        console.print(gmail_connect())
        return

    run_text_loop(mode_name=args.mode)

if __name__ == "__main__":
    main()
