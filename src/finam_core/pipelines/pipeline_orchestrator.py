from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from finam_core.pipelines.quote_normalizer import NormalizedQuote, QuoteNormalizer
from finam_core.pipelines.pipeline_kernel import PipelineKernel, PipelineKernelInput


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
        self.kernel = PipelineKernel(pipeline)

    def on_quote(self, context: QuoteEventContext) -> None:
        """Русский комментарий: нормализует quote и передаёт дальше в текущий pipeline."""
        normalized = QuoteNormalizer.normalize(context.event)

        return self.kernel.process_quote(
            PipelineKernelInput(
                event=normalized.raw_event,
                normalized_quote=normalized,
            )
        )
