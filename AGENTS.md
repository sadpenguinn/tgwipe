# tgwipe — Agent Reference

## Purpose
CLI tool that deletes the authenticated user's own messages in a specified Telegram chat, with optional date range filtering and optional AI-powered filtering via a configurable prompt. Uses Telegram MTProto API (not Bot API) via Telethon, and Claude API for analysis.

## Architecture

```
tgwipe/
├── cli.py            — Click entry point, wires all dependencies, bridges async→sync
├── config.py         — Config dataclass, loads from env/.env, validates required vars
├── domain/
│   ├── models.py     — Pure dataclasses: DateRange, MessageRecord, DeletionResult, MediaType
│   └── interfaces.py — MessageFetcher, MessageDeleter, MessageFilter Protocols
├── telegram/
│   ├── client.py     — TelegramClientWrapper: session reuse, interactive auth flow
│   ├── fetcher.py    — Fetcher: full history iteration with sender_id filter, optional media download
│   └── deleter.py    — Deleter + DryRunDeleter: chunked delete, FloodWaitError backoff
├── filters/
│   ├── cache.py      — AnalysisCache: SHA-256 keyed JSON cache in .wipecache/results.json
│   └── ai_filter.py  — AIFilter: batching + Claude vision, returns list[bool] per batch
├── service/
│   └── wipe.py       — WipeService: two-stage loop (analysis buffer → delete buffer)
└── ui/
    └── progress.py   — Rich progress bar, per-message verdict, result table
```

## Key Files

- `tgwipe/filters/ai_filter.py` — Builds Claude request with text + base64 images (photos/stickers), describes audio/video as `[type attachment]`. Parses JSON boolean array from response. Falls back to all-safe on parse error. Prompt and model come from config.
- `tgwipe/filters/cache.py` — `content_hash()` hashes media bytes if present, else full text. `set_batch()` writes all results from one analysis round in a single I/O call.
- `tgwipe/telegram/fetcher.py` — Iterates full chat history with `limit=None`, filters by `sender_id == me.id` client-side (avoids Telegram search API's 100-message cap). Downloads photos and static stickers (WebP) up to 5 MB when `include_media=True`.
- `tgwipe/service/wipe.py` — Maintains `analysis_buffer` (size=`ai_batch_size`) and `delete_buffer` (size=`batch_size`) independently. When filter is active, only records flagged `true` enter the delete buffer.
- `tgwipe/config.py` — All env var names defined here. Fails fast before any network call.

## Data Flow

### Without `--ai-filter`
```
cli.main()
  → Config.from_env()
  → TelegramClientWrapper.__aenter__()
  → WipeService.run()
      → Fetcher.fetch()  yields MessageRecord
      → delete_buffer fills to batch_size
      → Deleter.delete()
  → print_result()
```

### With `--ai-filter`
```
cli.main()
  → Config.from_env()  (requires ANTHROPIC_API_KEY + TGWIPE_AI_PROMPT)
  → TelegramClientWrapper.__aenter__()
  → AIFilter + AnalysisCache constructed
  → WipeService.run()
      → Fetcher.fetch(include_media=True)  yields MessageRecord with media_bytes
      → analysis_buffer fills to ai_batch_size
      → AIFilter.is_dangerous_batch()
          → check AnalysisCache per content_hash
          → uncached → Claude API (text + vision)
          → parse JSON boolean array
          → write new results to cache
      → true records → delete_buffer
      → Deleter.delete()
  → print_result()
```

## External Dependencies

- **Telegram MTProto API** — Telethon, requires `API_ID` + `API_HASH` from my.telegram.org
- **Claude API** — `anthropic.AsyncAnthropic(api_key=...)`, model configurable via `TGWIPE_AI_MODEL`; only active with `--ai-filter`
- **Session file** (`*.session`) — auth token, never committed
- **`.wipecache/results.json`** — AI analysis cache, never committed

## Domain Concepts

- `MediaType` — enum of Telegram media types: PHOTO, STICKER, GIF, AUDIO, VOICE, VIDEO, VIDEO_NOTE, DOCUMENT
- `MessageRecord` — immutable: id, date, preview (truncated), text (full), media_type, media_bytes
- `DateRange` — optional from/to UTC bounds
- `DeletionResult` — found / deleted / failed / skipped counts (`skipped` = filtered as safe by AI)
- `ai_batch_size` — messages per Claude request (default 10); separate from `batch_size` (Telegram delete limit, max 100)

## Development Notes

- `Fetcher` iterates full history and checks `message.sender_id == me_id` client-side. Using `from_user="me"` in `iter_messages` is avoided — it hits Telegram's search API which caps at 100 results.
- `--dry-run` and `--ai-filter` are mutually exclusive; `--dry-run` is silently ignored when `--ai-filter` is active.
- `AIFilter` requires `TGWIPE_AI_PROMPT` to be set; raises `ValueError` if missing.
- Vision is only sent when magic bytes confirm JPEG, PNG, WebP, or GIF format. Unrecognized formats (e.g. animated stickers) are described as `[type attachment]`.
- Cache key for media is the hash of raw bytes — same content in different messages is analyzed only once.
- `WipeService` has no imports from `telethon` or `anthropic` — depends only on Protocols.
- All datetimes are UTC-aware throughout the pipeline.

## Commands

```bash
uv sync              # install dependencies
uv run tgwipe --help # show help
uv build             # build the package
```
