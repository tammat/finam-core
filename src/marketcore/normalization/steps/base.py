from __future__ import annotations

from abc import ABC, abstractmethod
from time import perf_counter

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.steps.result import StepResult
from marketcore.normalization.steps.tags import StepTag


class BaseBuilderStep(ABC):
    name: str = "base"
    version: int = 1
    tags: tuple[StepTag, ...] = tuple()

    def run(self, ctx: NormalizationContext) -> StepResult:
        started = perf_counter()
        result = StepResult(success=True)

        try:
            result = self.execute(ctx)
            if result is None:
                result = StepResult(success=True)
        except Exception as exc:
            result = StepResult(
                success=False,
                errors=[f"{self.name}: {exc}"],
            )
            ctx.reject(f"{self.name.upper()}_EXCEPTION")

        duration_ms = int((perf_counter() - started) * 1000)
        result.duration_ms = duration_ms

        ctx.increment(f"step_{self.name}_duration_ms", duration_ms)
        ctx.increment(f"step_{self.name}_runs", 1)

        if result.rows_processed:
            ctx.increment(f"step_{self.name}_rows_processed", result.rows_processed)

        if result.rows_rejected:
            ctx.increment(f"step_{self.name}_rows_rejected", result.rows_rejected)

        if result.has_errors:
            ctx.increment(f"step_{self.name}_errors", len(result.errors))

        if result.has_warnings:
            ctx.increment(f"step_{self.name}_warnings", len(result.warnings))

        return result

    @abstractmethod
    def execute(self, ctx: NormalizationContext) -> StepResult:
        raise NotImplementedError
