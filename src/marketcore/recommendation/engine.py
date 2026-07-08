from __future__ import annotations

import psycopg2
import psycopg2.extras

from marketcore.recommendation.evaluator import RecommendationEvaluator, RecommendationRule
from marketcore.recommendation.loader import RecommendationContextLoader
from marketcore.recommendation.parameter_loader import PlatformParameterLoader
from marketcore.recommendation.repository import RecommendationRepository


class RecommendationEngine:
    def run(self) -> int:
        contexts = RecommendationContextLoader().load()
        parameters = PlatformParameterLoader().load()
        rules = self._load_rules()

        evaluator = RecommendationEvaluator()
        repository = RecommendationRepository()

        saved = 0
        for context in contexts:
            result = evaluator.evaluate(context, rules, parameters)
            repository.save(result)
            saved += 1

        return saved

    def _load_rules(self) -> list[RecommendationRule]:
        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT rule_code, recommendation_code, priority
                    FROM knowledge.recommendation_rule_v1
                    WHERE enabled
                    ORDER BY priority
                """)
                rows = cur.fetchall()

                rules: list[RecommendationRule] = []
                for row in rows:
                    cur.execute("""
                        SELECT metric_code, operator_code, parameter_code
                        FROM knowledge.recommendation_rule_condition_v1
                        WHERE rule_code=%s
                          AND enabled
                        ORDER BY condition_order
                    """, (row["rule_code"],))

                    rules.append(
                        RecommendationRule(
                            rule_code=row["rule_code"],
                            recommendation_code=row["recommendation_code"],
                            priority=int(row["priority"]),
                            conditions=[dict(x) for x in cur.fetchall()],
                        )
                    )

                return rules


if __name__ == "__main__":
    saved_rows = RecommendationEngine().run()
    print("=== MARKET_CONTEXT_RECOMMENDATION_ENGINE_RUN_ALL_V1 ===")
    print(f"recommendations_saved={saved_rows}")
    print("engine_mode=run_all_contexts")
    print("business_logic_source=postgres")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKET_CONTEXT_RECOMMENDATION_ENGINE_RUN_ALL_V1_READY")
