from __future__ import annotations

import uuid

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.steps import (
    BaseBuilderStep,
    StepResult,
    StepTag,
)

BAR_EVENT_NOT_READY = "BAR_EVENT_NOT_READY"


class BuildLineageStep(BaseBuilderStep):
    name = "build_lineage"
    version = 1
    tags = (StepTag.LINEAGE,)

    def execute(self, ctx: NormalizationContext) -> StepResult:

        if not hasattr(ctx, "bar_event"):
            ctx.reject(BAR_EVENT_NOT_READY)
            ctx.add_quality_event(
                {
                    "reason": BAR_EVENT_NOT_READY,
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

        lineage = {
            "lineage_uuid": str(uuid.uuid4()),
            "root_entity_uuid": ctx.event_uuid,
            "source_entity_uuid": ctx.raw.source_key,
            "target_entity_uuid": ctx.event_uuid,
            "relationship": "NORMALIZED_FROM",
            "stage": "NORMALIZATION",
            "depth": 1,
            "valid": True,
        }

        ctx.lineage_edges.append(lineage)
        ctx.increment("lineage_built")

        return StepResult(
            success=True,
            rows_processed=1,
        )
