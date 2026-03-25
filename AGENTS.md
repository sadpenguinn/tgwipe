# tgwipe — Agent Reference

## Purpose
CLI tool that deletes the authenticated user's own messages in a specified Telegram chat, with optional date range filtering. Uses Telegram MTProto API (not Bot API) via Telethon.

## Architecture

```
tgwipe/
├── cli.py            — Click entry point, wires all dependencies, bridges async→sync
├── config.py         — Config dataclass, loads from env/.env, validates required vars
├── domain/
│   ├── models.py     — Pure dataclasses: DateRange, MessageRecord, DeletionResult
│   └── interfaces.py — MessageFetcher and MessageDeleter Protocols (structural typing)
├── telegram/
│   ├── client.py     — TelegramClientWrapper: session reuse, interactive auth flow
│   ├── fetcher.py    — Fetcher: paginates iter_messages(from_user="me"), early-stop on from_date
│   └── deleter.py    — Deleter: chunked delete (max 100/request), FloodWaitError backoff
├── service/
│   └── wipe.py       — WipeService: fetch→buffer→delete loop, accumulates DeletionResult
└── ui/
    └── progress.py   — Rich progress bar, result table, error/info helpers
```

## Key Files

- `tgwipe/telegram/fetcher.py` — Core pagination. Uses `offset_date=to_date` for API-side upper bound, breaks on `from_date` since messages come newest-first.
- `tgwipe/telegram/deleter.py` — Chunked deletion with `FloodWaitError` retry. Never deletes non-own messages (Telethon rejects it at API level).
- `tgwipe/service/wipe.py` — Only file that touches both fetcher and deleter. Buffer flush on loop end handles partial batches.
- `tgwipe/config.py` — All env var names defined here. Fails fast before any network call.

## Data Flow

```
cli.main()
  → Config.from_env()
  → TelegramClientWrapper.__aenter__()  (auth if needed)
  → WipeService.run(chat_id, date_range, batch_size, on_found)
      → Fetcher.fetch()  yields MessageRecord
      → [buffer fills to batch_size]
      → Deleter.delete()  returns count
  → print_result()
```

## External Dependencies

- **Telegram MTProto API** — Telethon library, requires API_ID + API_HASH from my.telegram.org
- **Session file** (`*.session`) — stores auth token locally, never committed to git

## Domain Concepts

- `DateRange` — optional from/to UTC bounds; `contains(dt)` checks membership
- `MessageRecord` — immutable snapshot: id, date, text preview
- `DeletionResult` — mutable accumulator: found / deleted / failed counts
- `batch_size` — messages buffered before a delete API call (max 100 per Telegram limit)

## Development Notes

- `Fetcher` uses `reverse=False` (newest-first). The `from_date` early-stop relies on this ordering — do not change.
- `Deleter._delete_chunk` loops on `FloodWaitError` until success; `MessageDeleteForbiddenError` returns 0 silently.
- `WipeService` does not import anything from `telethon` — depends only on Protocols.
- All datetimes are UTC-aware. `cli._to_utc_start` sets time=00:00:00, `_to_utc_end` sets time=23:59:59.
- Session files must stay in `.gitignore` — they contain authentication tokens.

## Commands

```bash
uv sync              # install dependencies
uv run tgwipe --help # show help
uv build             # build the package
```
