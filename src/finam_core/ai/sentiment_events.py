from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TelegramSentimentEvent:
    """
    Русский комментарий:
    Событие AI-анализа текста.
    Не содержит торговых команд.
    """

    ts: str
    source: str
    text: str
    label: str
    score: float
    raw: dict[str, Any]
