from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TelegramAdvisorySendResultV1:
    dry_run: bool
    sent: bool
    chat_id: str
    symbol: str
    severity: str
    category: str
    text: str


class TelegramAdvisorySenderDryRunV1:
    """
    Русский комментарий:
    Dry-run sender для advisory-сообщений.
    Реальную отправку в Telegram не выполняет.
    Нужен для проверки payload и будущего notifier pipeline.
    """

    def __init__(self, *, chat_id: str = "DRY_RUN_CHAT") -> None:
        self.chat_id = chat_id

    def send(
        self,
        *,
        symbol: str,
        severity: str,
        category: str,
        text: str,
    ) -> TelegramAdvisorySendResultV1:
        print(
            "TELEGRAM_ADVISORY_DRY_RUN_SEND",
            f"chat_id={self.chat_id}",
            f"symbol={symbol}",
            f"severity={severity}",
            f"category={category}",
            f"text_len={len(text)}",
            flush=True,
        )

        return TelegramAdvisorySendResultV1(
            dry_run=True,
            sent=False,
            chat_id=self.chat_id,
            symbol=symbol,
            severity=severity,
            category=category,
            text=text,
        )
