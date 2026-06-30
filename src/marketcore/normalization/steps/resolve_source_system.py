from __future__ import annotations

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.steps import BaseBuilderStep, StepResult, StepTag


UNKNOWN_SOURCE_SYSTEM = "UNKNOWN_SOURCE_SYSTEM"


class ResolveSourceSystemStep(BaseBuilderStep):
    name = "resolve_source_system"
    version = 1
    tags = (StepTag.RESOLUTION,)

    def execute(self, ctx: NormalizationContext) -> StepResult:
        source_code = (ctx.raw.source_system_code or "").strip()

        if not source_code:
            ctx.reject(UNKNOWN_SOURCE_SYSTEM)
            ctx.add_quality_event({
                "reason": UNKNOWN_SOURCE_SYSTEM,
                "severity": "HIGH",
                "blocks_research": True,
                "blocks_ai": True,
                "blocks_runtime": True,
                "message": "source_system_code is empty",
            })
            return StepResult(success=False, rows_processed=1, rows_rejected=1)

        resolvers = getattr(ctx, "resolvers", None)
        if resolvers is None:
            ctx.reject("RESOLVER_REGISTRY_MISSING")
            ctx.add_quality_event({
                "reason": "RESOLVER_REGISTRY_MISSING",
                "severity": "HIGH",
                "blocks_research": True,
                "blocks_ai": True,
                "blocks_runtime": True,
                "message": "ctx.resolvers is missing",
            })
            return StepResult(success=False, rows_processed=1, rows_rejected=1)

        row = resolvers.source_system.resolve(resolvers.conn, source_code)

        if not row:
            ctx.reject(UNKNOWN_SOURCE_SYSTEM)
            ctx.add_quality_event({
                "reason": UNKNOWN_SOURCE_SYSTEM,
                "severity": "HIGH",
                "blocks_research": True,
                "blocks_ai": True,
                "blocks_runtime": True,
                "message": f"source_system_code not found: {source_code}",
            })
            return StepResult(success=False, rows_processed=1, rows_rejected=1)

        ctx.source_system_id = int(row["id"])
        ctx.source_system = row
        ctx.increment("source_system_resolved", 1)

        return StepResult(success=True, rows_processed=1)
