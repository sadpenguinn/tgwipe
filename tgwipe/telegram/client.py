from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from tgwipe.config import Config


class TelegramClientWrapper:
    """Manages Telegram client lifecycle and authentication."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = TelegramClient(
            config.session_name,
            config.api_id,
            config.api_hash,
        )

    async def __aenter__(self) -> TelegramClient:
        await self._client.connect()
        if not await self._client.is_user_authorized():
            await self._authenticate()
        return self._client

    async def __aexit__(self, *args: object) -> None:
        await self._client.disconnect()

    async def _authenticate(self) -> None:
        """Interactive auth: prompts for SMS code and 2FA password if needed."""
        await self._client.send_code_request(self._config.phone)

        code = input("Enter the Telegram confirmation code: ").strip()
        try:
            await self._client.sign_in(self._config.phone, code)
        except SessionPasswordNeededError:
            password = input("Enter your two-factor authentication password: ").strip()
            await self._client.sign_in(password=password)
