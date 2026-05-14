from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QuoteEventContext:
    """Русский комментарий: нормализованный контекст quote-события для orchestration layer."""
    event: Any


class PipelineOrchestrator:
    """
    Русский комментарий:
    Pipeline Orchestrator Layer.

    Этап 1:
    тонкая безопасная обёртка над текущим PaperTradingPipeline._on_quote_impl().
    Дальше сюда по одному будут переноситься:
    - quote normalization;
    - signal processing;
    - risk routing;
    - execution routing;
    - lifecycle routing.
    """

    def __init__(self, pipeline) -> None:
        self.pipeline = pipeline

    def on_quote(self, context: QuoteEventContext) -> None:
        return self.pipeline._on_quote_impl(context.event)
