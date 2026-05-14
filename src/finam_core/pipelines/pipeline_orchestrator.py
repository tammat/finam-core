from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from finam_core.pipelines.quote_normalizer import NormalizedQuote, QuoteNormalizer


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
        """Русский комментарий: нормализует quote и передаёт дальше в текущий pipeline."""
        normalized = QuoteNormalizer.normalize(context.event)

        return self.pipeline._on_quote_impl(
            normalized.raw_event
        )
