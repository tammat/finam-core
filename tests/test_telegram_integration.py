import os
import pytest

from src.telegram_bot import TelegramBot


@pytest.mark.integration
def test_telegram_real_send():
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")

    if not token or not chat_id:
        pytest.skip("Telegram integration not configured")

    bot = TelegramBot(token=token, chat_id=chat_id)

    # Если исключений нет — тест пройден
    bot.send("Integration test message from Finam_Core")