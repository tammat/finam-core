from __future__ import annotations

import os
import uuid

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
POLICY_CODE = "DYNAMIC_EDGE_PRIORITY_V1"


def main() -> None:
    decision_batch_id = uuid.uuid4()
    with psycopg2.connect(DB) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO analytics.microstructure_priority_decision_v1
                    (decision_batch_id,symbol,priority_rank,priority_score,
                     selected_for_detail,selected_for_analysis,reason_code,evidence,policy_code)
                SELECT %s,symbol,priority_rank,priority_score,selected_for_detail,
                       selected_for_analysis,reason_code,
                       jsonb_build_object(
                         'waiting_candidates',waiting_candidates,
                         'coverage_pct',coverage_pct,
                         'matched_trades',matched_trades,
                         'eligible_trades',eligible_trades,
                         'information_value_score',information_value_score,
                         'capacity_rub',capacity_rub,
                         'max_abs_correlation',max_abs_correlation,
                         'fills_1h',fills_1h,
                         'last_quote_at',last_quote_at,
                         'deep_quotes_15m',deep_quotes_15m
                       ),policy_code
                FROM analytics.microstructure_research_priority_v1
                ORDER BY priority_rank
                """,
                (str(decision_batch_id),),
            )
            rows = cursor.rowcount
    print(f"decision_batch_id={decision_batch_id}")
    print(f"priorities_recorded={rows}")
    print(f"policy_code={POLICY_CODE}")
    print("VERDICT=MICROSTRUCTURE_PRIORITIES_REFRESHED")


if __name__ == "__main__":
    main()
