"""Notification channels. Telegram now; WhatsApp Cloud API can implement the same `Notifier` later."""
import logging
from typing import Protocol

import httpx

from ..config import get_settings

log = logging.getLogger(__name__)


class Notifier(Protocol):
    channel: str

    def send(self, chat_id: str, text: str) -> None: ...


class TelegramNotifier:
    channel = "telegram"

    def __init__(self, token: str):
        self.token = token

    def send(self, chat_id: str, text: str) -> None:
        r = httpx.post(
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        r.raise_for_status()


class ConsoleNotifier:
    """Used when no Telegram token is configured: logs instead of sending."""
    channel = "console"

    def send(self, chat_id: str, text: str) -> None:
        log.info("[console notifier] to=%s\n%s", chat_id, text)


def get_notifier() -> Notifier:
    token = get_settings().telegram_bot_token
    return TelegramNotifier(token) if token else ConsoleNotifier()


def deep_link(prefix: str, token: str) -> str | None:
    """t.me link that links a Telegram chat to a user ('u') or customer ('c')."""
    bot = get_settings().telegram_bot_username
    return f"https://t.me/{bot}?start={prefix}_{token}" if bot else None
