from __future__ import annotations

import json

import psycopg2

from marketcore.recommendation.execution_context_models import (
    RecommendationExecutionContext,
)

SOURCE_VERSION = "RECOMMENDATION_EXECUTION_CONTEXT_MODELS_V1"


class RecommendationExecutionContextRepository:

    def save(
        self,
        context: RecommendationExecutionContext,
    ) -> int:

        with psycopg2.connect(
            "postgresql:///finam_core"
        ) as conn:

            with conn.cursor() as cur:

                cur.execute(
                    """
                    INSERT INTO
                    knowledge.recommendation_execution_context_v1
                    (
                        recommendation_id,

                        direction_code,

                        entry_price,

                        invalidation_price,

                        target_price,

                        horizon_bars,

                        risk_unit,

                        source_context_id,

                        source_edge_context_id,

                        execution_allowed,

                        runtime_allowed,

                        micro_live_allowed,

                        evidence_json,

                        source_version
                    )
                    VALUES
                    (
                        %s,%s,%s,%s,%s,
                        %s,%s,%s,%s,
                        0,
                        0,
                        0,
                        %s::jsonb,
                        %s
                    )
                    RETURNING execution_context_id
                    """,
                    (
                        context.recommendation_id,
                        context.direction_code,
                        context.entry_price,
                        context.invalidation_price,
                        context.target_price,
                        context.horizon_bars,
                        context.risk_unit,
                        context.source_context_id,
                        context.source_edge_context_id,
                        json.dumps(
                            context.evidence,
                            ensure_ascii=False,
                        ),
                        SOURCE_VERSION,
                    ),
                )

                return int(cur.fetchone()[0])
