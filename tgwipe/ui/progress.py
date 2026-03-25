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
    """Displays real-time progress with a Rich progress bar."""

    def __init__(self, dry_run: bool = False, ai_filter: bool = False) -> None:
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("[dim]{task.fields[status]}"),
            console=console,
        )
        if dry_run:
            label = "Scanning messages (dry run)..."
        elif ai_filter:
            label = "Scanning and analyzing messages..."
        else:
            label = "Scanning and deleting messages..."

        self._task_id = self._progress.add_task(label, total=None, status="")

    def on_found(self, record: MessageRecord) -> None:
        self._progress.advance(self._task_id)
        self._progress.update(
            self._task_id,
            status=record.preview[:50] if record.preview else "",
        )

    def on_analyzed(self, record: MessageRecord, is_dangerous: bool) -> None:
        verdict = "[red]DELETE[/red]" if is_dangerous else "[green]safe[/green]"
        self._progress.update(
            self._task_id,
            status=f"{verdict}  {record.preview[:40] if record.preview else ''}",
        )

    @contextmanager
    def live(self) -> Generator[None, None, None]:
        with Live(self._progress, console=console, refresh_per_second=10):
            yield


def print_result(
    result: DeletionResult,
    chat_id: int | str,
    dry_run: bool = False,
    ai_filter: bool = False,
) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column(style="bold")

    table.add_row("Chat", str(chat_id))
    table.add_row("Messages found", str(result.total_found))

    if dry_run:
        table.add_row("Would delete", f"[yellow]{result.total_found}[/yellow]")
    else:
        if ai_filter:
            table.add_row("Flagged as dangerous", str(result.total_deleted + result.total_failed))
            table.add_row("Skipped as safe", str(result.total_skipped))
        table.add_row("Deleted", f"[green]{result.total_deleted}[/green]")
        if result.total_failed:
            table.add_row("Failed", f"[red]{result.total_failed}[/red]")

    if dry_run:
        title = "[bold]Dry run result[/bold]"
    elif ai_filter:
        title = "[bold]AI filter result[/bold]"
    else:
        title = "[bold]Result[/bold]"

    console.print(Panel(table, title=title, expand=False))


def print_error(message: str) -> None:
    console.print(f"[bold red]Error:[/bold red] {message}")


def print_info(message: str) -> None:
    console.print(f"[dim]{message}[/dim]")
