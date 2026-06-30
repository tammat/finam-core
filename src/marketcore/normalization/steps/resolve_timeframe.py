from __future__ import annotations

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.steps import (
    BaseBuilderStep,
    StepResult,
    StepTag,
)

UNKNOWN_TIMEFRAME = "UNKNOWN_TIMEFRAME"


class ResolveTimeframeStep(BaseBuilderStep):
    name = "resolve_timeframe"
    version = 1
    tags = (StepTag.RESOLUTION,)

    def execute(self, ctx: NormalizationContext) -> StepResult:

        timeframe = (ctx.raw.timeframe_code or "").strip()

        if not timeframe:
            ctx.reject(UNKNOWN_TIMEFRAME)
            ctx.add_quality_event(
                {
                    "reason": UNKNOWN_TIMEFRAME,
                    "blocks_research": True,
                    "blocks_ai": True,
                    "blocks_runtime": True,
                }
            )
            return StepResult(
                success=False,
                rows_processed=1,
                rows_rejected=1,
            )

        row = ctx.resolvers.timeframe.resolve(
            ctx.resolvers.conn,
            timeframe,
        )

        if row is None:
            ctx.reject(UNKNOWN_TIMEFRAME)
            ctx.add_quality_event(
                {
                    "reason": UNKNOWN_TIMEFRAME,
                    "blocks_research": True,
                    "blocks_ai": True,
                    "blocks_runtime": True,
                }
            )
            return StepResult(
                success=False,
                rows_processed=1,
                rows_rejected=1,
            )

        ctx.timeframe_id = int(row["id"])
        ctx.timeframe = row

        ctx.increment("timeframe_resolved")

        return StepResult(
            success=True,
            rows_processed=1,
        )
