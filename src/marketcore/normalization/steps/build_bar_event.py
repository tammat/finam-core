from __future__ import annotations

import uuid

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.steps import (
    BaseBuilderStep,
    StepResult,
    StepTag,
)

MISSING_RESOLUTION = "MISSING_RESOLUTION"


class BuildBarEventStep(BaseBuilderStep):
    name = "build_bar_event"
    version = 1
    tags = (StepTag.BUILD,)

    def execute(self, ctx: NormalizationContext) -> StepResult:

        required = (
            ("source_system", getattr(ctx, "source_system", None)),
            ("symbol_alias", getattr(ctx, "symbol_alias", None)),
            ("instrument", getattr(ctx, "instrument", None)),
            ("contract", getattr(ctx, "contract", None)),
            ("timeframe", getattr(ctx, "timeframe", None)),
        )

        missing = [name for name, value in required if value is None]

        if missing:
            ctx.reject(MISSING_RESOLUTION)
            ctx.add_quality_event(
                {
                    "reason": MISSING_RESOLUTION,
                    "missing": missing,
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

        ctx.event_uuid = str(uuid.uuid4())

        ctx.bar_event = {
            "event_uuid": ctx.event_uuid,
            "event_type": "BAR_EVENT",
            "source_system_id": ctx.source_system_id,
            "symbol_alias_id": ctx.symbol_alias_id,
            "instrument_id": ctx.instrument_id,
            "contract_id": ctx.contract_id,
            "timeframe_id": ctx.timeframe_id,
            "event_time": ctx.raw.event_time,
            "source_time": ctx.raw.source_time,
            "received_at": ctx.raw.received_at,
            "open": ctx.raw.open,
            "high": ctx.raw.high,
            "low": ctx.raw.low,
            "close": ctx.raw.close,
            "volume": ctx.raw.volume,
            "payload": ctx.raw.payload,
        }

        ctx.increment("bar_events_built")

        return StepResult(
            success=True,
            rows_processed=1,
        )
