from __future__ import annotations

from decimal import Decimal

import psycopg2
import psycopg2.extras

from marketcore.recommendation.execution_context_models import RecommendationExecutionContext
from marketcore.recommendation.execution_context_repository import RecommendationExecutionContextRepository


SOURCE_VERSION = "RECOMMENDATION_EXECUTION_CONTEXT_BUILDER_V1"


class RecommendationExecutionContextBuilder:
    def build_all(self) -> int:
        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT DISTINCT ON (r.symbol, r.timeframe)
                        r.recommendation_id,
                        r.symbol,
                        r.timeframe,
                        r.evidence_json,
                        mc.context_id,
                        ec.edge_context_id,
                        ec.edge_score_v2,
                        ec.regime_code
                    FROM knowledge.recommendation_result_v1 r
                    JOIN knowledge.market_context_v1 mc
                      ON mc.context_id=(r.evidence_json->>'market_context_id')::bigint
                    JOIN knowledge.edge_context_v1 ec
                      ON ec.edge_context_id=(r.evidence_json->>'edge_context_id')::bigint
                    WHERE r.evidence_json ? 'market_context_id'
                      AND r.evidence_json ? 'edge_context_id'
                    ORDER BY r.symbol, r.timeframe, r.created_at DESC
                """)
                rows = cur.fetchall()

        repo = RecommendationExecutionContextRepository()
        created = 0

        for row in rows:
            plan = self._build_one(row)
            repo.save(plan)
            created += 1

        return created

    def _build_one(self, row: dict) -> RecommendationExecutionContext:
        edge_score = Decimal(str(row["edge_score_v2"] or 0))

        direction_code = self._direction_from_regime(str(row["regime_code"] or ""))

        entry_price = Decimal("1")
        invalidation_price = Decimal("1")
        target_price = Decimal("1")
        risk_unit = Decimal("1")

        return RecommendationExecutionContext(
            recommendation_id=int(row["recommendation_id"]),
            direction_code=direction_code,
            entry_price=entry_price,
            invalidation_price=invalidation_price,
            target_price=target_price,
            stop_loss_price=invalidation_price,
            take_profit_price=target_price,
            trailing_enabled=False,
            trailing_step=Decimal("0"),
            trailing_activation_price=Decimal("0"),
            horizon_bars=1,
            risk_unit=risk_unit,
            source_context_id=int(row["context_id"]),
            source_edge_context_id=int(row["edge_context_id"]),
            evidence={
                "source_version": SOURCE_VERSION,
                "builder_mode": "trading_plan_skeleton",
                "edge_score_v2": str(edge_score),
                "execution_allowed": 0,
                "runtime_allowed": 0,
                "micro_live_allowed": 0,
            },
        )

    def _direction_from_regime(self, regime_code: str) -> str:
        regime = regime_code.upper()
        if "DOWN" in regime:
            return "DIRECTION_DOWN"
        if "UP" in regime:
            return "DIRECTION_UP"
        return "DIRECTION_NEUTRAL"


if __name__ == "__main__":
    created = RecommendationExecutionContextBuilder().build_all()
    print("=== RECOMMENDATION_EXECUTION_CONTEXT_BUILDER_V1 ===")
    print(f"execution_context_rows_created={created}")
    print("builder_mode=trading_plan_skeleton")
    print("execution_allowed=0")
    print("runtime_allowed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=RECOMMENDATION_EXECUTION_CONTEXT_BUILDER_V1_READY")
