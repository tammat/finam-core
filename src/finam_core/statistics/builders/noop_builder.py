# -*- coding: utf-8 -*-
from __future__ import annotations

from finam_core.statistics.builders.base_builder import FactBuilder
from finam_core.statistics.pipeline.builder_context import BuilderContext
from finam_core.statistics.pipeline.builder_result import BuilderResult


class NoopFactBuilder(FactBuilder):
    def build(self, context: BuilderContext) -> BuilderResult:
        return BuilderResult(
            status="PLANNED",
            rows_in=0,
            rows_out=0,
            duplicate_rows=0,
            error_rows=0,
            health_score=100,
            health_light="GREEN",
            health_reason_code="OK",
            reason="FACT_BUILDER_FRAMEWORK_READY",
            payload={
                "builder_name": context.builder_name,
                "fact_domain": context.fact_domain,
                "fact_type": context.fact_type,
                "framework_only": True,
            },
        )
