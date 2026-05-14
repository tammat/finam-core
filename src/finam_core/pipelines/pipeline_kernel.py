from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PipelineKernelInput:
    """Русский комментарий: нормализованный вход ядра pipeline."""
    event: Any
    normalized_quote: Any | None = None


class PipelineKernel:
    """
    Русский комментарий:
    Pipeline Kernel — центральное ядро orchestration.

    Этап 1:
    thin-wrapper над текущим pipeline._on_quote_impl().
    Поведение не меняем.
    """

    def __init__(self, pipeline) -> None:
        self.pipeline = pipeline

    def process_quote(self, data: PipelineKernelInput) -> None:
        return self.pipeline._on_quote_impl(data.event)
