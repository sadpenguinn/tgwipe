from dataclasses import dataclass
from datetime import datetime, timezone


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


@dataclass
class DeletionResult:
    total_found: int = 0
    total_deleted: int = 0
    total_failed: int = 0

    def record_deleted(self, count: int) -> None:
        self.total_deleted += count

    def record_failed(self, count: int) -> None:
        self.total_failed += count

    def record_found(self) -> None:
        self.total_found += 1
