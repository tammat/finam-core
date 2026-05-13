from __future__ import annotations

from typing import Any

from finam_core.ai.sentiment_feature_provider import SentimentFeatureProvider


class SentimentSignalEnricher:
    """
    Русский комментарий:
    Обогащает features сигнала AI-сентиментом.
    Не принимает торговых решений и не отправляет заявки.
    """

    def __init__(self, provider: SentimentFeatureProvider | None = None) -> None:
        self.provider = provider or SentimentFeatureProvider()

    def enrich(self, symbol: str, features: dict[str, Any] | None = None) -> dict[str, Any]:
        result = dict(features or {})

        try:
            result.update(self.provider.latest_features_dict(symbol=symbol))
        except Exception as exc:
            result.update(
                {
                    "ai_sentiment_label": "unavailable",
                    "ai_sentiment_score": 0.0,
                    "ai_sentiment_source": "error",
                    "ai_sentiment_error": str(exc),
                }
            )

        return result
