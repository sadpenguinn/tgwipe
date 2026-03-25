from collections.abc import AsyncIterator
from datetime import timezone

from telethon import TelegramClient

from tgwipe.config import Config
from tgwipe.domain.models import DateRange, MediaType, MessageRecord

_PREVIEW_MAX_LEN = 60
# Skip download for files larger than 5 MB to avoid slow requests
_MAX_MEDIA_BYTES = 5 * 1024 * 1024

# Media types that Claude vision can process as images
_VISION_TYPES = {MediaType.PHOTO, MediaType.STICKER}


class Fetcher:
    """Iterates the authenticated user's own messages in a chat, respecting the date range."""

    def __init__(
        self,
        client: TelegramClient,
        config: Config,
        include_media: bool = False,
    ) -> None:
        self._client = client
        self._config = config
        self._include_media = include_media

    async def fetch(
        self, chat_id: int | str, date_range: DateRange
    ) -> AsyncIterator[MessageRecord]:
        # Resolve current user ID once — used for client-side sender filtering.
        # We do NOT use iter_messages(from_user="me") because that goes through
        # Telegram's search API which caps results at 100 regardless of limit.
        # Instead we walk the full history and skip messages from other senders.
        me = await self._client.get_me()
        me_id = me.id

        kwargs: dict = {
            "limit": None,    # fetch all messages in the range
            "reverse": False, # newest-first; required for the from_date early-stop below
        }
        if date_range.to_date:
            # offset_date is an exclusive upper bound at the API level
            kwargs["offset_date"] = date_range.to_date

        async for message in self._client.iter_messages(chat_id, **kwargs):
            # Messages arrive newest-first; once we cross from_date all remaining
            # messages are older, so we can stop regardless of who sent them.
            if date_range.from_date and message.date:
                msg_dt = message.date.replace(tzinfo=timezone.utc)
                if msg_dt < date_range.from_date:
                    return

            if not message.id or not message.date:
                continue

            if message.sender_id != me_id:
                continue

            text = message.text or ""
            media_type = _detect_media_type(message)
            media_bytes: bytes | None = None

            if self._include_media and media_type in _VISION_TYPES:
                media_bytes = await _download_media(self._client, message)

            yield MessageRecord(
                id=message.id,
                date=message.date,
                preview=_make_preview(text),
                text=text,
                media_type=media_type,
                media_bytes=media_bytes,
            )


def _detect_media_type(message) -> MediaType | None:
    if message.photo:
        return MediaType.PHOTO
    if message.sticker:
        return MediaType.STICKER
    if message.gif:
        return MediaType.GIF
    if message.voice:
        return MediaType.VOICE
    if message.video_note:
        return MediaType.VIDEO_NOTE
    if message.video:
        return MediaType.VIDEO
    if message.audio:
        return MediaType.AUDIO
    if message.document:
        return MediaType.DOCUMENT
    return None


async def _download_media(client: TelegramClient, message) -> bytes | None:
    """Download media bytes; returns None if the file is too large or download fails."""
    try:
        doc = message.document
        if doc and doc.size > _MAX_MEDIA_BYTES:
            return None
        data = await client.download_media(message, file=bytes)
        return data if isinstance(data, bytes) else None
    except Exception:
        return None


def _make_preview(text: str) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= _PREVIEW_MAX_LEN:
        return text
    return text[:_PREVIEW_MAX_LEN] + "..."
