import asyncio

from telethon import TelegramClient
from telethon.errors import FloodWaitError, MessageDeleteForbiddenError

from tgwipe.config import Config

# Telegram allows deleting at most 100 messages per request
_MAX_CHUNK = 100


class Deleter:
    """Deletes messages in chunks, handling FloodWaitError with automatic backoff."""

    def __init__(self, client: TelegramClient, config: Config) -> None:
        self._client = client
        self._config = config

    async def delete(self, chat_id: int | str, message_ids: list[int]) -> int:
        """Returns the number of successfully deleted messages."""
        deleted = 0
        for chunk in _chunked(message_ids, _MAX_CHUNK):
            deleted += await self._delete_chunk(chat_id, chunk)
        return deleted

    async def _delete_chunk(self, chat_id: int | str, ids: list[int]) -> int:
        while True:
            try:
                await self._client.delete_messages(chat_id, ids)
                await asyncio.sleep(self._config.request_delay)
                return len(ids)
            except FloodWaitError as exc:
                # Wait exactly as long as Telegram requires, plus one second buffer
                await asyncio.sleep(exc.seconds + 1)
            except MessageDeleteForbiddenError:
                # No permission to delete these messages; skip silently
                return 0


class DryRunDeleter:
    """No-op deleter for --dry-run mode; reports success without touching the API."""

    async def delete(self, chat_id: int | str, message_ids: list[int]) -> int:
        return len(message_ids)


def _chunked(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]
