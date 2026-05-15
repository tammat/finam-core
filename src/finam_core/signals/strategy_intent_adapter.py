from __future__ import annotations

from typing import Any

from finam_core.signals.signal_intent import SignalIntent


class StrategyIntentAdapter:
    """
    Русский комментарий:
    Adapter layer:

    legacy strategy dict
        ↓
    canonical SignalIntent v2

    И обратно:
    SignalIntent
        ↓
    dict for old pipeline
    """

    @staticmethod
    def normalize(intent: Any) -> SignalIntent | None:
        """
        Русский комментарий:
        Приводит strategy output к SignalIntent.
        """

        if intent is None:
            return None

        if isinstance(intent, SignalIntent):
            return intent

        if isinstance(intent, dict):
            return SignalIntent.from_dict(intent)

        raise TypeError(
            f"Unsupported strategy intent type: {type(intent).__name__}"
        )

    @staticmethod
    def to_pipeline_dict(intent: Any) -> dict | None:
        """
        Русский комментарий:
        Временный compatibility bridge для paper_pipeline.py.
        """

        normalized = StrategyIntentAdapter.normalize(intent)

        if normalized is None:
            return None

        return normalized.to_dict()
