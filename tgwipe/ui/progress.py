from collections.abc import Generator
from contextlib import contextmanager

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

from tgwipe.domain.models import DeletionResult, MessageRecord

console = Console()


class ProgressTracker:
    """Displays real-time deletion progress with a Rich progress bar."""

    def __init__(self, dry_run: bool = False) -> None:
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("[dim]{task.fields[preview]}"),
            console=console,
        )
        label = "Scanning messages (dry run)..." if dry_run else "Scanning and deleting messages..."
        self._task_id = self._progress.add_task(label, total=None, preview="")

    def update(self, record: MessageRecord) -> None:
        self._progress.advance(self._task_id)
        self._progress.update(
            self._task_id,
            preview=record.preview[:50] if record.preview else "",
        )

    @contextmanager
    def live(self) -> Generator[None, None, None]:
        with Live(self._progress, console=console, refresh_per_second=10):
            yield


def print_result(result: DeletionResult, chat_id: int | str, dry_run: bool = False) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column(style="bold")

    table.add_row("Chat", str(chat_id))
    table.add_row("Messages found", str(result.total_found))

    if dry_run:
        table.add_row("Would delete", f"[yellow]{result.total_found}[/yellow]")
    else:
        table.add_row("Deleted", f"[green]{result.total_deleted}[/green]")
        if result.total_failed:
            table.add_row("Failed", f"[red]{result.total_failed}[/red]")

    title = "[bold]Dry run result[/bold]" if dry_run else "[bold]Result[/bold]"
    console.print(Panel(table, title=title, expand=False))


def print_error(message: str) -> None:
    console.print(f"[bold red]Error:[/bold red] {message}")


def print_info(message: str) -> None:
    console.print(f"[dim]{message}[/dim]")
