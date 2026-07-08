from __future__ import annotations

import json

import psycopg2

from marketcore.recommendation.evaluator import EvaluatedRecommendation

SOURCE_VERSION = "MARKET_CONTEXT_RECOMMENDATION_REPOSITORY_V1"


class RecommendationRepository:
    def save(self, result: EvaluatedRecommendation) -> int:
        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO knowledge.recommendation_result_v1
                    (
                        symbol,
                        timeframe,
                        recommendation_code,
                        recommendation_confidence,
                        rule_code,
                        knowledge_version,
                        evidence_json,
                        source_version
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
                    RETURNING recommendation_id
                    """,
                    (
                        result.symbol,
                        result.timeframe,
                        result.recommendation_code,
                        result.recommendation_confidence,
                        result.rule_code,
                        "MARKET_KNOWLEDGE_V1",
                        json.dumps(result.evidence, ensure_ascii=False),
                        SOURCE_VERSION,
                    ),
                )

                recommendation_id = int(cur.fetchone()[0])

                for idx, reason in enumerate(result.reasons, start=1):
                    cur.execute(
                        """
                        INSERT INTO knowledge.recommendation_reason_v1
                        (
                            recommendation_id,
                            reason_order,
                            reason_code,
                            reason_value,
                            confidence,
                            source_version
                        )
                        VALUES (%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            recommendation_id,
                            idx,
                            reason.get("reason_code"),
                            reason.get("reason_value"),
                            reason.get("confidence"),
                            SOURCE_VERSION,
                        ),
                    )

                return recommendation_id
