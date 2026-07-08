from __future__ import annotations

from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras

from marketcore.recommendation.models import RecommendationContext


class RecommendationContextLoader:
    def load(self) -> list[RecommendationContext]:
        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    WITH latest_market_context AS (
                        SELECT DISTINCT ON (symbol, timeframe)
                            *
                        FROM knowledge.market_context_v1
                        WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1'
                        ORDER BY symbol, timeframe, created_at DESC
                    ),
                    latest_edge_context AS (
                        SELECT DISTINCT ON (symbol, timeframe)
                            *
                        FROM knowledge.edge_context_v1
                        WHERE source_version='MARKETCORE_MARKET_KNOWLEDGE_EDGE_CONTEXT_BRIDGE_V1'
                        ORDER BY symbol, timeframe, created_at DESC
                    )
                    SELECT
                        mc.context_id AS market_context_id,
                        ec.edge_context_id,
                        mc.symbol,
                        mc.timeframe,
                        ec.edge_score_v2,
                        mc.regime_code,
                        mc.volatility_state,
                        mc.liquidity_state,
                        mc.volume_state,
                        mc.spread_state,
                        mc.session_state,
                        mc.correlation_state,
                        mc.sector_strength_state,
                        (
                            (
                                (mc.regime_code <> 'UNKNOWN')::int +
                                (mc.volatility_state <> 'UNKNOWN')::int +
                                (mc.liquidity_state <> 'UNKNOWN')::int +
                                (mc.volume_state <> 'UNKNOWN')::int +
                                (mc.spread_state <> 'UNKNOWN')::int +
                                (mc.session_state <> 'UNKNOWN')::int +
                                (mc.correlation_state <> 'UNKNOWN')::int +
                                (mc.sector_strength_state <> 'UNKNOWN')::int
                            )::numeric / 8
                        ) AS knowledge_coverage
                    FROM latest_market_context mc
                    JOIN latest_edge_context ec
                      ON ec.symbol=mc.symbol
                     AND ec.timeframe=mc.timeframe
                    WHERE ec.edge_score_v2 IS NOT NULL
                    ORDER BY mc.symbol, mc.timeframe
                """)
                rows = list(cur.fetchall())

                result: list[RecommendationContext] = []

                for row in rows:
                    cur.execute(
                        """
                        SELECT source_code, relation_type, target_code, weight, confidence, evidence_json
                        FROM knowledge.relationship_v1
                        WHERE source_version='MARKET_CONTEXT_CORRELATION_COLLECTOR_V1'
                          AND is_active
                          AND (
                               source_code=%s
                            OR target_code=%s
                          )
                        ORDER BY confidence DESC NULLS LAST
                        """,
                        (row["symbol"], row["symbol"]),
                    )
                    relationships: list[dict[str, Any]] = [dict(r) for r in cur.fetchall()]

                    result.append(
                        RecommendationContext(
                            symbol=str(row["symbol"]),
                            timeframe=str(row["timeframe"]),
                            edge_score=Decimal(str(row["edge_score_v2"])),
                            market_context_id=int(row["market_context_id"]),
                            edge_context_id=int(row["edge_context_id"]),
                            knowledge_coverage=Decimal(str(row["knowledge_coverage"])),
                            regime_code=str(row["regime_code"]),
                            volatility_state=str(row["volatility_state"]),
                            liquidity_state=str(row["liquidity_state"]),
                            volume_state=str(row["volume_state"]),
                            spread_state=str(row["spread_state"]),
                            session_state=str(row["session_state"]),
                            correlation_state=str(row["correlation_state"]),
                            sector_strength_state=str(row["sector_strength_state"]),
                            relationships=relationships,
                        )
                    )

                return result
