import pytest
from unittest.mock import patch

from src.telegram_bot import TelegramBot


def test_send_calls_requests_post():
    bot = TelegramBot(token="test_token", chat_id="123")

    with patch("src.telegram_bot.requests.post") as mock_post:
        bot.send("hello")

        mock_post.assert_called_once()

        args, kwargs = mock_post.call_args

        assert "https://api.telegram.org/bottest_token/sendMessage" in args[0]
        assert kwargs["json"]["chat_id"] == "123"
        assert kwargs["json"]["text"] == "hello"


def test_send_does_not_raise_on_exception():
    bot = TelegramBot(token="test_token", chat_id="123")

    with patch("src.telegram_bot.requests.post", side_effect=Exception):
        # не должно выбрасывать исключение
        bot.send("fail")