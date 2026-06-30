from __future__ import annotations

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.steps import (
    BaseBuilderStep,
    StepResult,
    StepTag,
)

UNKNOWN_SYMBOL_ALIAS = "UNKNOWN_SYMBOL_ALIAS"
SOURCE_SYSTEM_NOT_RESOLVED = "SOURCE_SYSTEM_NOT_RESOLVED"


class ResolveSymbolAliasStep(BaseBuilderStep):
    name = "resolve_symbol_alias"
    version = 1
    tags = (StepTag.RESOLUTION,)

    def execute(self, ctx: NormalizationContext) -> StepResult:

        if ctx.source_system_id is None:
            ctx.reject(SOURCE_SYSTEM_NOT_RESOLVED)
            ctx.add_quality_event(
                {
                    "reason": SOURCE_SYSTEM_NOT_RESOLVED,
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

        symbol = (ctx.raw.symbol_code or "").strip()

        if not symbol:
            ctx.reject(UNKNOWN_SYMBOL_ALIAS)
            ctx.add_quality_event(
                {
                    "reason": UNKNOWN_SYMBOL_ALIAS,
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

        key = f"{ctx.source_system_id}::{symbol}"

        row = ctx.resolvers.symbol_alias.resolve(
            ctx.resolvers.conn,
            key,
        )

        if row is None:
            ctx.reject(UNKNOWN_SYMBOL_ALIAS)
            ctx.add_quality_event(
                {
                    "reason": UNKNOWN_SYMBOL_ALIAS,
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

        ctx.symbol_alias_id = int(row["id"])
        ctx.symbol_alias = row

        ctx.increment("symbol_alias_resolved")

        return StepResult(
            success=True,
            rows_processed=1,
        )
