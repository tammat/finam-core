from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SentimentResult:
    label: str
    score: float
    raw: dict[str, Any]


class SentimentEngine:
    """
    Русский комментарий:
    AI-слой только анализирует текст и возвращает sentiment.
    Он не имеет права отправлять заявки напрямую.
    """

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or "mxlcw/rubert-tiny2-russian-economic-sentiment"
        self._pipeline = None

    def _lazy_load(self) -> None:
        if self._pipeline is not None:
            return

        try:
            from transformers import pipeline
        except Exception as exc:
            raise RuntimeError(
                "Не установлен transformers. Выполните: pip install transformers torch"
            ) from exc

        self._pipeline = pipeline(
            "text-classification",
            model=self.model_name,
            tokenizer=self.model_name,
        )

    def analyze(self, text: str) -> SentimentResult:
        if not text or not text.strip():
            return SentimentResult(
                label="neutral",
                score=0.0,
                raw={"reason": "empty_text"},
            )

        self._lazy_load()

        assert self._pipeline is not None
        result = self._pipeline(text[:2000])[0]

        label = str(result.get("label", "unknown")).lower()
        score = float(result.get("score", 0.0))

        return SentimentResult(
            label=label,
            score=score,
            raw=dict(result),
        )
