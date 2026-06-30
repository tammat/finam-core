from __future__ import annotations

from time import perf_counter

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.hooks import NormalizationHooks
from marketcore.normalization.metrics import NormalizationMetrics
from marketcore.normalization.pipeline import NormalizationPipeline, PipelineStep
from marketcore.normalization.result import NormalizationResult


class MarketDataNormalizationBuilder:
    builder_version = "MARKET_DATA_NORMALIZATION_BUILDER_V1"
    pipeline_version = "NORMALIZATION_PIPELINE_V1"

    def __init__(
        self,
        steps: tuple[PipelineStep, ...],
        hooks: NormalizationHooks | None = None,
        stop_on_reject: bool = True,
    ) -> None:
        self.pipeline = NormalizationPipeline(
            steps=steps,
            stop_on_reject=stop_on_reject,
        )
        self.hooks = hooks or NormalizationHooks()

    def run(self, ctx: NormalizationContext) -> NormalizationResult:
        started = perf_counter()
        errors: list[str] = []

        try:
            ctx.metrics["builder_version"] = 1
            ctx.metrics["pipeline_version"] = 1
            self.hooks.before_pipeline(ctx)

            for step in self.pipeline.steps:
                self.hooks.before_step(step.name, ctx)

            ctx = self.pipeline.run(ctx)

            for step in self.pipeline.steps:
                self.hooks.after_step(step.name, ctx)

            self.hooks.after_pipeline(ctx)

        except Exception as exc:
            ctx.reject("BUILDER_EXCEPTION")
            errors.append(str(exc))

        duration_ms = int((perf_counter() - started) * 1000)

        metrics = NormalizationMetrics(
            rows_total=ctx.metrics.get("rows_total", 1),
            rows_new=ctx.metrics.get("rows_new", 0),
            rows_updated=ctx.metrics.get("rows_updated", 0),
            rows_rejected=ctx.metrics.get("rows_rejected", 0),
            quality_events=len(ctx.quality_events),
            lineage_edges=len(ctx.lineage_edges),
            duration_ms=duration_ms,
        )

        return NormalizationResult(
            success=not ctx.rejected and not errors,
            metrics=metrics,
            errors=errors,
            payload={
                "event_uuid": ctx.event_uuid,
                "rejection_reason": ctx.rejection_reason,
                "raw_source_key": ctx.raw.source_key,
            },
        )
