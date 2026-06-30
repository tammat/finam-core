from __future__ import annotations

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.steps import (
    BaseBuilderStep,
    StepResult,
    StepTag,
)

UNKNOWN_INSTRUMENT = "UNKNOWN_INSTRUMENT"
SYMBOL_ALIAS_NOT_RESOLVED = "SYMBOL_ALIAS_NOT_RESOLVED"


class ResolveInstrumentStep(BaseBuilderStep):
    name = "resolve_instrument"
    version = 1
    tags = (StepTag.RESOLUTION,)

    def execute(self, ctx: NormalizationContext) -> StepResult:

        if getattr(ctx, "symbol_alias", None) is None:
            ctx.reject(SYMBOL_ALIAS_NOT_RESOLVED)
            ctx.add_quality_event({
                "reason": SYMBOL_ALIAS_NOT_RESOLVED,
                "blocks_research": True,
                "blocks_ai": True,
                "blocks_runtime": True,
            })
            return StepResult(
                success=False,
                rows_processed=1,
                rows_rejected=1,
            )

        instrument_id = ctx.symbol_alias.get("instrument_id")

        if instrument_id is None:
            ctx.reject(UNKNOWN_INSTRUMENT)
            ctx.add_quality_event({
                "reason": UNKNOWN_INSTRUMENT,
                "blocks_research": True,
                "blocks_ai": True,
                "blocks_runtime": True,
            })
            return StepResult(
                success=False,
                rows_processed=1,
                rows_rejected=1,
            )

        row = ctx.resolvers.instrument.resolve(
            ctx.resolvers.conn,
            str(instrument_id),
        )

        if row is None:
            ctx.reject(UNKNOWN_INSTRUMENT)
            ctx.add_quality_event({
                "reason": UNKNOWN_INSTRUMENT,
                "blocks_research": True,
                "blocks_ai": True,
                "blocks_runtime": True,
            })
            return StepResult(
                success=False,
                rows_processed=1,
                rows_rejected=1,
            )

        ctx.instrument_id = int(row["id"])
        ctx.instrument = row

        ctx.increment("instrument_resolved")

        return StepResult(
            success=True,
            rows_processed=1,
        )
