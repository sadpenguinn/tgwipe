from collections.abc import Callable

from tgwipe.domain.interfaces import MessageDeleter, MessageFetcher
from tgwipe.domain.models import DateRange, DeletionResult, MessageRecord


class WipeService:
    """Orchestrates fetching and deleting the user's own messages."""

    def __init__(self, fetcher: MessageFetcher, deleter: MessageDeleter) -> None:
        self._fetcher = fetcher
        self._deleter = deleter

    async def run(
        self,
        chat_id: int | str,
        date_range: DateRange,
        batch_size: int,
        on_found: Callable[[MessageRecord], None],
    ) -> DeletionResult:
        result = DeletionResult()
        buffer: list[int] = []

        async for record in self._fetcher.fetch(chat_id, date_range):
            result.record_found()
            buffer.append(record.id)
            on_found(record)

            if len(buffer) >= batch_size:
                deleted = await self._deleter.delete(chat_id, buffer)
                result.record_deleted(deleted)
                result.record_failed(len(buffer) - deleted)
                buffer.clear()

        # Flush remaining messages that didn't fill a full batch
        if buffer:
            deleted = await self._deleter.delete(chat_id, buffer)
            result.record_deleted(deleted)
            result.record_failed(len(buffer) - deleted)

        return result
