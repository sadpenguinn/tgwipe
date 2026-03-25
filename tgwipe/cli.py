import asyncio
import sys
from datetime import datetime, time, timezone

import click

from tgwipe.config import Config, ConfigError
from tgwipe.domain.models import DateRange
from tgwipe.service.wipe import WipeService
from tgwipe.telegram.client import TelegramClientWrapper
from tgwipe.telegram.deleter import Deleter, DryRunDeleter
from tgwipe.telegram.fetcher import Fetcher
from tgwipe.ui.progress import ProgressTracker, print_error, print_info, print_result


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument("chat_id", type=click.UNPROCESSED)
@click.option(
    "--from-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Start of date range (inclusive), format: YYYY-MM-DD",
)
@click.option(
    "--to-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="End of date range (inclusive), format: YYYY-MM-DD",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview messages that would be deleted without actually deleting them.",
)
def main(chat_id: str, from_date: datetime | None, to_date: datetime | None, dry_run: bool) -> None:
    """Delete your own messages in the specified Telegram chat.

    CHAT_ID can be a numeric chat ID or @username.
    """
    try:
        config = Config.from_env()
    except ConfigError as exc:
        print_error(str(exc))
        sys.exit(1)

    date_range = DateRange(
        from_date=_to_utc_start(from_date),
        to_date=_to_utc_end(to_date),
    )

    _print_plan(chat_id, date_range, dry_run)

    try:
        asyncio.run(_run(chat_id, date_range, config, dry_run))
    except KeyboardInterrupt:
        print_info("\nInterrupted by user.")
        sys.exit(0)


async def _run(chat_id: str, date_range: DateRange, config: Config, dry_run: bool) -> None:
    async with TelegramClientWrapper(config) as client:
        fetcher = Fetcher(client, config)
        deleter = DryRunDeleter() if dry_run else Deleter(client, config)
        service = WipeService(fetcher, deleter)

        tracker = ProgressTracker(dry_run=dry_run)

        with tracker.live():
            result = await service.run(
                chat_id=_parse_chat_id(chat_id),
                date_range=date_range,
                batch_size=config.batch_size,
                on_found=tracker.update,
            )

    print_result(result, chat_id, dry_run=dry_run)


def _parse_chat_id(value: str) -> int | str:
    """Returns an integer if value is numeric, otherwise returns as-is (@username)."""
    try:
        return int(value)
    except ValueError:
        return value


def _to_utc_start(dt: datetime | None) -> datetime | None:
    """Converts a date to start-of-day UTC (00:00:00)."""
    if dt is None:
        return None
    return datetime.combine(dt.date(), time.min, tzinfo=timezone.utc)


def _to_utc_end(dt: datetime | None) -> datetime | None:
    """Converts a date to end-of-day UTC (23:59:59)."""
    if dt is None:
        return None
    return datetime.combine(dt.date(), time.max, tzinfo=timezone.utc)


def _print_plan(chat_id: str, date_range: DateRange, dry_run: bool) -> None:
    from tgwipe.ui.progress import console

    parts = [f"Chat: [bold]{chat_id}[/bold]"]
    if date_range.from_date:
        parts.append(f"from [bold]{date_range.from_date.date()}[/bold]")
    if date_range.to_date:
        parts.append(f"to [bold]{date_range.to_date.date()}[/bold]")
    if dry_run:
        parts.append("[yellow bold](dry run)[/yellow bold]")
    console.print("  ".join(parts))
