from collections.abc import AsyncIterator
from typing import Protocol

from tgwipe.domain.models import DateRange, MessageRecord


class MessageFetcher(Protocol):
    async def fetch(
        self, chat_id: int | str, date_range: DateRange
    ) -> AsyncIterator[MessageRecord]: ...


class MessageDeleter(Protocol):
    async def delete(self, chat_id: int | str, message_ids: list[int]) -> int: ...


class MessageFilter(Protocol):
    async def is_dangerous_batch(self, records: list[MessageRecord]) -> list[bool]: ...
