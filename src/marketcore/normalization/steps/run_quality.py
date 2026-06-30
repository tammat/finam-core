from __future__ import annotations

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.steps import (
    BaseBuilderStep,
    StepResult,
    StepTag,
)


class RunQualityStep(BaseBuilderStep):
    name = "run_quality"
    version = 1
    tags = (StepTag.QUALITY,)

    def execute(self, ctx: NormalizationContext) -> StepResult:

        if ctx.rejected:
            return StepResult(
                success=False,
                rows_processed=1,
                rows_rejected=1,
            )

        if not hasattr(ctx, "bar_event"):
            ctx.reject("BAR_EVENT_NOT_BUILT")
            ctx.add_quality_event(
                {
                    "reason": "BAR_EVENT_NOT_BUILT",
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

        ctx.quality_status_id = 1
        ctx.quality_status = {
            "id": 1,
            "entity_code": "VALID",
        }

        ctx.bar_event["quality_status_id"] = ctx.quality_status_id
        ctx.bar_event["research_ready"] = True
        ctx.bar_event["ai_ready"] = True

        ctx.increment("quality_passed")

        return StepResult(
            success=True,
            rows_processed=1,
        )
