from __future__ import annotations

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.steps import (
    BaseBuilderStep,
    StepResult,
    StepTag,
)

UNKNOWN_CONTRACT = "UNKNOWN_CONTRACT"
SYMBOL_ALIAS_NOT_RESOLVED = "SYMBOL_ALIAS_NOT_RESOLVED"


class ResolveContractStep(BaseBuilderStep):
    name = "resolve_contract"
    version = 1
    tags = (StepTag.RESOLUTION,)

    def execute(self, ctx: NormalizationContext) -> StepResult:

        if getattr(ctx, "symbol_alias", None) is None:
            ctx.reject(SYMBOL_ALIAS_NOT_RESOLVED)
            ctx.add_quality_event(
                {
                    "reason": SYMBOL_ALIAS_NOT_RESOLVED,
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

        contract_id = ctx.symbol_alias.get("contract_id")

        if contract_id is None:
            ctx.reject(UNKNOWN_CONTRACT)
            ctx.add_quality_event(
                {
                    "reason": UNKNOWN_CONTRACT,
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

        row = ctx.resolvers.contract.resolve(
            ctx.resolvers.conn,
            str(contract_id),
        )

        if row is None:
            ctx.reject(UNKNOWN_CONTRACT)
            ctx.add_quality_event(
                {
                    "reason": UNKNOWN_CONTRACT,
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

        ctx.contract_id = int(row["id"])
        ctx.contract = row

        ctx.increment("contract_resolved")

        return StepResult(
            success=True,
            rows_processed=1,
        )
