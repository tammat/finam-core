from __future__ import annotations

import os

import psycopg2

from marketcore.normalization.context import NormalizationContext
from marketcore.normalization.steps import (
    BaseBuilderStep,
    StepResult,
    StepTag,
)


class PersistLineageStep(BaseBuilderStep):
    name = "persist_lineage"
    version = 1
    tags = (StepTag.PERSIST,)

    def execute(self, ctx: NormalizationContext) -> StepResult:

        if not ctx.lineage_edges:
            return StepResult(success=True)

        conn = getattr(ctx.resolvers, "conn", None)

        if conn is None:
            conn = psycopg2.connect(
                os.getenv("DATABASE_URL", "postgresql:///finam_core")
            )

        sql = """
        INSERT INTO warehouse.normalized_lineage_event_v1
        (
            lineage_uuid,
            root_entity_uuid,
            source_entity_uuid,
            target_entity_uuid,
            relationship_type_id,
            lineage_stage,
            lineage_depth,
            lineage_valid,
            graph_node_uuid
        )
        VALUES
        (
            %(lineage_uuid)s,
            %(root_entity_uuid)s,
            %(source_entity_uuid)s,
            %(target_entity_uuid)s,
            (
                SELECT id
                FROM warehouse.normalized_lineage_relationship_type_v1
                WHERE entity_code=%(relationship)s
                LIMIT 1
            ),
            %(stage)s,
            %(depth)s,
            %(valid)s,
            gen_random_uuid()
        )
        ON CONFLICT DO NOTHING
        """

        with conn.cursor() as cur:
            for edge in ctx.lineage_edges:
                cur.execute(sql, edge)

        conn.commit()

        ctx.increment("lineage_events_persisted")

        return StepResult(
            success=True,
            rows_processed=len(ctx.lineage_edges),
        )
