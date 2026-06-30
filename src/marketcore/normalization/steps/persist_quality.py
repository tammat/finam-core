from __future__ import annotations

import os
import psycopg2

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.steps import (
    BaseBuilderStep,
    StepResult,
    StepTag,
)


class PersistQualityStep(BaseBuilderStep):
    name = "persist_quality"
    version = 1
    tags = (StepTag.PERSIST,)

    def execute(self, ctx: NormalizationContext) -> StepResult:

        if not ctx.quality_events:
            return StepResult(success=True)

        conn = getattr(ctx.resolvers, "conn", None)

        if conn is None:
            conn = psycopg2.connect(
                os.getenv("DATABASE_URL", "postgresql:///finam_core")
            )

        sql = """
        INSERT INTO warehouse.normalized_data_quality_event_v1
        (
            quality_event_uuid,
            affected_event_uuid,
            quality_reason_id,
            blocks_research,
            blocks_ai,
            blocks_runtime,
            resolved,
            payload
        )
        VALUES
        (
            gen_random_uuid(),
            %(affected_event_uuid)s,
            %(quality_reason_id)s,
            %(blocks_research)s,
            %(blocks_ai)s,
            %(blocks_runtime)s,
            false,
            %(payload)s
        )
        """

        with conn.cursor() as cur:
            for event in ctx.quality_events:
                cur.execute(
                    sql,
                    {
                        "affected_event_uuid": ctx.event_uuid,
                        "quality_reason_id": event.get("quality_reason_id", 1),
                        "blocks_research": event.get("blocks_research", True),
                        "blocks_ai": event.get("blocks_ai", True),
                        "blocks_runtime": event.get("blocks_runtime", True),
                        "payload": event,
                    },
                )

        conn.commit()

        ctx.increment("quality_events_persisted")

        return StepResult(
            success=True,
            rows_processed=len(ctx.quality_events),
        )
