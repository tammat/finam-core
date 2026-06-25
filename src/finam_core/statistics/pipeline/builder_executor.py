# -*- coding: utf-8 -*-
from __future__ import annotations

from finam_core.statistics.pipeline.builder_context import BuilderContext
from finam_core.statistics.pipeline.builder_registry import BuilderRegistry
from finam_core.statistics.pipeline.builder_result import BuilderResult


class BuilderExecutor:
    def __init__(self, registry: BuilderRegistry | None = None) -> None:
        self._registry = registry or BuilderRegistry()

    def execute(self, context: BuilderContext) -> BuilderResult:
        builder = self._registry.get(context.builder_name)
        if builder is None:
            return BuilderResult(
                status="FAILED",
                rows_in=0,
                rows_out=0,
                duplicate_rows=0,
                error_rows=1,
                health_score=0,
                health_light="RED",
                health_reason_code="BUILDER_NOT_FOUND",
                reason=f"BUILDER_NOT_FOUND:{context.builder_name}",
                payload={"builder_name": context.builder_name},
            )
        return builder.build(context)
