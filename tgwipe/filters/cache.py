import hashlib
import json
from pathlib import Path

from tgwipe.domain.models import MessageRecord

_CACHE_DIR = Path(".wipecache")
_CACHE_FILE = _CACHE_DIR / "results.json"


class AnalysisCache:
    """Persists AI analysis results keyed by SHA-256 of message content."""

    def __init__(self) -> None:
        self._data: dict[str, bool] = {}
        self._load()

    def get(self, key: str) -> bool | None:
        return self._data.get(key)

    def set(self, key: str, value: bool) -> None:
        self._data[key] = value
        self._save()

    def set_batch(self, entries: dict[str, bool]) -> None:
        """Write multiple results at once to avoid repeated I/O."""
        self._data.update(entries)
        self._save()

    def _load(self) -> None:
        if _CACHE_FILE.exists():
            try:
                self._data = json.loads(_CACHE_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def _save(self) -> None:
        _CACHE_DIR.mkdir(exist_ok=True)
        _CACHE_FILE.write_text(json.dumps(self._data, indent=2))


def content_hash(record: MessageRecord) -> str:
    """SHA-256 of media bytes (if present) or full message text."""
    h = hashlib.sha256()
    if record.media_bytes:
        h.update(record.media_bytes)
    else:
        h.update(record.text.encode())
    return h.hexdigest()
