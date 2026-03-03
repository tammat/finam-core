import requests


class TelegramBot:
    def __init__(self, token: str, chat_id: str):
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id

    def send(self, text: str):
        try:
            requests.post(
                self.url,
                json={"chat_id": self.chat_id, "text": text},
                timeout=5,
            )
        except Exception:
            pass  # никогда не ломаем трейдинг из-за Telegram