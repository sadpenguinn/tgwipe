import base64
import json
import re

import anthropic

from tgwipe.config import Config
from tgwipe.domain.models import MediaType, MessageRecord
from tgwipe.filters.cache import AnalysisCache, content_hash

_MAX_TOKENS = 1024


def _detect_mime(data: bytes) -> str | None:
    """Detect image MIME type from magic bytes. Returns None for unsupported formats."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return None

class AIFilter:
    """Classifies messages as dangerous/safe using Claude with batching and vision."""

    def __init__(self, client: anthropic.AsyncAnthropic, cache: AnalysisCache, config: Config) -> None:
        if not config.ai_prompt:
            raise ValueError("TGWIPE_AI_PROMPT is not set. Add it to your .env file.")
        self._client = client
        self._cache = cache
        self._model = config.ai_model
        self._prompt = config.ai_prompt

    async def is_dangerous_batch(self, records: list[MessageRecord]) -> list[bool]:
        """Returns True for each record that should be deleted."""
        results: list[bool | None] = [None] * len(records)
        uncached_records: list[MessageRecord] = []
        uncached_indices: list[int] = []

        for i, record in enumerate(records):
            key = content_hash(record)
            cached = self._cache.get(key)
            if cached is not None:
                results[i] = cached
            else:
                uncached_records.append(record)
                uncached_indices.append(i)

        if uncached_records:
            ai_results = await self._analyze(uncached_records)
            new_entries: dict[str, bool] = {}
            for idx, record, is_dangerous in zip(uncached_indices, uncached_records, ai_results):
                results[idx] = is_dangerous
                new_entries[content_hash(record)] = is_dangerous
            self._cache.set_batch(new_entries)

        # Any None remaining (shouldn't happen) defaults to safe
        return [bool(r) for r in results]

    async def _analyze(self, records: list[MessageRecord]) -> list[bool]:
        content = _build_content(records)
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=_MAX_TOKENS,
            system=self._prompt,
            messages=[{"role": "user", "content": content}],
        )
        if not response.content:
            return [False] * len(records)
        return _parse_response(response.content[0].text, len(records))


def _build_content(records: list[MessageRecord]) -> list[dict]:
    content: list[dict] = []

    for i, record in enumerate(records, 1):
        content.append({"type": "text", "text": f"\n--- Message {i} ---"})

        mime = _detect_mime(record.media_bytes) if record.media_bytes else None
        if mime:
            # Send image for visual analysis only when format is confirmed valid
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime,
                    "data": base64.standard_b64encode(record.media_bytes).decode(),
                },
            })
        elif record.media_type:
            # Describe non-visual media so Claude still sees it
            content.append({"type": "text", "text": f"[{record.media_type.value} attachment]"})

        if record.text:
            content.append({"type": "text", "text": record.text})
        elif not record.media_type:
            content.append({"type": "text", "text": "[empty message]"})

    content.append({
        "type": "text",
        "text": (
            f"\nAnalyze each of the {len(records)} messages above. "
            "Respond with a JSON array of booleans only."
        ),
    })
    return content


def _parse_response(text: str, expected: int) -> list[bool]:
    match = re.search(r"\[[\s\S]*?]", text)
    if match:
        try:
            result = json.loads(match.group())
            if len(result) == expected:
                return [bool(x) for x in result]
        except (json.JSONDecodeError, TypeError):
            pass
    # Fallback: treat all as safe to avoid unintended deletions
    return [False] * expected
