from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class MediaType(str, Enum):
    PHOTO = "photo"
    STICKER = "sticker"
    GIF = "gif"
    AUDIO = "audio"
    VOICE = "voice"
    VIDEO = "video"
    VIDEO_NOTE = "video_note"
    DOCUMENT = "document"


@dataclass(frozen=True)
class DateRange:
    from_date: datetime | None = None
    to_date: datetime | None = None

    def contains(self, dt: datetime) -> bool:
        """Returns True if dt falls within the range (inclusive)."""
        dt_utc = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        if self.from_date and dt_utc < self.from_date:
            return False
        if self.to_date and dt_utc > self.to_date:
            return False
        return True

    def is_empty(self) -> bool:
        return self.from_date is None and self.to_date is None


@dataclass(frozen=True)
class MessageRecord:
    id: int
    date: datetime
    preview: str
    # Full untruncated text, used by AI filter
    text: str = ""
    # Present only when fetcher downloads media (include_media=True)
    media_type: MediaType | None = None
    media_bytes: bytes | None = None


@dataclass
class DeletionResult:
    total_found: int = 0
    total_deleted: int = 0
    total_failed: int = 0
    # Set when AI filter is active
    total_skipped: int = 0

    def record_deleted(self, count: int) -> None:
        self.total_deleted += count

    def record_failed(self, count: int) -> None:
        self.total_failed += count

    def record_found(self) -> None:
        self.total_found += 1

    def record_skipped(self, count: int) -> None:
        self.total_skipped += count
