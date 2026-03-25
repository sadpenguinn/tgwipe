from collections.abc import AsyncIterator
from datetime import timezone

from telethon import TelegramClient

from tgwipe.config import Config
from tgwipe.domain.models import DateRange, MessageRecord

_PREVIEW_MAX_LEN = 60


class Fetcher:
    """Iterates the authenticated user's own messages in a chat, respecting the date range."""

    def __init__(self, client: TelegramClient, config: Config) -> None:
        self._client = client
        self._config = config

    async def fetch(
        self, chat_id: int | str, date_range: DateRange
    ) -> AsyncIterator[MessageRecord]:
        # offset_date acts as an upper bound (exclusive) at the API level,
        # so passing to_date here avoids fetching messages beyond the range over the wire.
        kwargs: dict = {
            "from_user": "me",
            "reverse": False,  # newest-first; required for the from_date early-stop below
        }
        if date_range.to_date:
            kwargs["offset_date"] = date_range.to_date

        async for message in self._client.iter_messages(chat_id, **kwargs):
            # Messages arrive newest-first, so once we pass from_date we can stop early.
            if date_range.from_date and message.date:
                msg_dt = message.date.replace(tzinfo=timezone.utc)
                if msg_dt < date_range.from_date:
                    return

            if message.id and message.date:
                yield MessageRecord(
                    id=message.id,
                    date=message.date,
                    preview=_make_preview(message.text or ""),
                )


def _make_preview(text: str) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= _PREVIEW_MAX_LEN:
        return text
    return text[:_PREVIEW_MAX_LEN] + "..."
