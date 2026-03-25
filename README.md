# tgwipe

CLI tool that deletes **your own** messages in a specified Telegram chat.

## Description

Connects to your account via the Telegram MTProto API and deletes only your messages in the given chat. Supports optional date range filtering.

## Dependencies

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) — package manager
- A Telegram account with API credentials from [my.telegram.org](https://my.telegram.org)

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=0123456789abcdef0123456789abcdef
TELEGRAM_PHONE=+12025551234
```

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_API_ID` | yes | App ID from my.telegram.org |
| `TELEGRAM_API_HASH` | yes | App hash from my.telegram.org |
| `TELEGRAM_PHONE` | yes | Phone number of your account |
| `TGWIPE_SESSION_NAME` | no | Session file name (default: `tgwipe`) |
| `TGWIPE_REQUEST_DELAY` | no | Pause between requests in seconds (default: `0.5`) |
| `TGWIPE_BATCH_SIZE` | no | Message buffer size before deletion (default: `100`) |

## Run

```bash
# Install dependencies
uv sync

# Delete all your messages in a chat
uv run tgwipe @username

# With a date range
uv run tgwipe @username --from-date 2024-01-01 --to-date 2024-06-30

# Using a numeric chat ID
uv run tgwipe 123456789 --from-date 2025-01-01
```

On the first run the tool will prompt for a Telegram confirmation code (and a 2FA password if enabled). The session is saved to `tgwipe.session` and reused on subsequent runs.

## Build

```bash
uv build
```
