from collections.abc import Callable

from tgwipe.domain.interfaces import MessageDeleter, MessageFetcher, MessageFilter
from tgwipe.domain.models import DateRange, DeletionResult, MessageRecord


class WipeService:
    """Orchestrates fetching, optional AI filtering, and deletion of the user's own messages."""

    def __init__(
        self,
        fetcher: MessageFetcher,
        deleter: MessageDeleter,
        message_filter: MessageFilter | None = None,
        ai_batch_size: int = 10,
    ) -> None:
        self._fetcher = fetcher
        self._deleter = deleter
        self._filter = message_filter
        self._ai_batch_size = ai_batch_size

    async def run(
        self,
        chat_id: int | str,
        date_range: DateRange,
        delete_batch_size: int,
        on_found: Callable[[MessageRecord], None],
        on_analyzed: Callable[[MessageRecord, bool], None] | None = None,
    ) -> DeletionResult:
        result = DeletionResult()
        delete_buffer: list[int] = []
        analysis_buffer: list[MessageRecord] = []

        async for record in self._fetcher.fetch(chat_id, date_range):
            result.record_found()
            on_found(record)

            if self._filter:
                analysis_buffer.append(record)
                if len(analysis_buffer) >= self._ai_batch_size:
                    await self._flush_analysis(
                        chat_id, analysis_buffer, delete_buffer, result, on_analyzed
                    )
                    analysis_buffer.clear()
            else:
                delete_buffer.append(record.id)

            if len(delete_buffer) >= delete_batch_size:
                await self._flush_deletions(chat_id, delete_buffer, result)
                delete_buffer.clear()

        # Flush remaining analysis batch
        if analysis_buffer and self._filter:
            await self._flush_analysis(
                chat_id, analysis_buffer, delete_buffer, result, on_analyzed
            )

        # Flush remaining deletions
        if delete_buffer:
            await self._flush_deletions(chat_id, delete_buffer, result)

        return result

    async def _flush_analysis(
        self,
        chat_id: int | str,
        batch: list[MessageRecord],
        delete_buffer: list[int],
        result: DeletionResult,
        on_analyzed: Callable[[MessageRecord, bool], None] | None,
    ) -> None:
        flags = await self._filter.is_dangerous_batch(batch)
        for record, is_dangerous in zip(batch, flags):
            if on_analyzed:
                on_analyzed(record, is_dangerous)
            if is_dangerous:
                delete_buffer.append(record.id)
            else:
                result.record_skipped(1)

    async def _flush_deletions(
        self,
        chat_id: int | str,
        buffer: list[int],
        result: DeletionResult,
    ) -> None:
        deleted = await self._deleter.delete(chat_id, buffer)
        result.record_deleted(deleted)
        result.record_failed(len(buffer) - deleted)
        buffer.clear()
