from rich.console import Console
from core.router import route_command

console = Console()

def main():
    console.print("[bold cyan]Jarvis Desktop Agent[/bold cyan]")
    console.print("Type a command. Example: open email, open chrome, find resume")
    console.print("Type 'exit' to quit.\n")

    while True:
        command = console.input("[bold green]You:[/bold green] ")

        if command.lower().strip() in ["exit", "quit"]:
            console.print("[bold cyan]Jarvis shutting down.[/bold cyan]")
            break

        result = route_command(command)
        console.print(f"[bold blue]Jarvis:[/bold blue] {result}\n")

if __name__ == "__main__":
    main()