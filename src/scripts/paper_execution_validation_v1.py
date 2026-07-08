from __future__ import annotations

import json
from decimal import Decimal

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "PAPER_EXECUTION_VALIDATION_V1"


def _load_integer_parameter(cur, code: str) -> int:
    cur.execute(
        """
        SELECT parameter_value
        FROM knowledge.platform_parameter_v1
        WHERE parameter_code=%s
          AND enabled
        """,
        (code,),
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"missing platform parameter: {code}")
    return int(Decimal(str(row["parameter_value"])))


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            min_future_bars = _load_integer_parameter(cur, "PAPER_VALIDATION_MIN_FUTURE_BARS")

            cur.execute(
                """
                SELECT DISTINCT ON (symbol, timeframe)
                    recommendation_id,
                    symbol,
                    timeframe,
                    recommendation_code,
                    recommendation_confidence,
                    evidence_json,
                    created_at
                FROM knowledge.recommendation_result_v1
                ORDER BY symbol, timeframe, created_at DESC
                """
            )
            recommendations = cur.fetchall()

            inserted = 0

            for rec in recommendations:
                cur.execute(
                    """
                    SELECT count(*) AS bars_after
                    FROM public.market_bars
                    WHERE symbol=%s
                      AND timeframe=%s
                      AND ts > %s
                    """,
                    (rec["symbol"], rec["timeframe"], rec["created_at"]),
                )
                bars_after = int(cur.fetchone()["bars_after"] or 0)

                evidence = dict(rec["evidence_json"] or {})
                has_direction = bool(evidence.get("direction"))
                has_entry = bool(evidence.get("entry_price"))
                has_exit = bool(evidence.get("exit_price"))

                if not has_direction or not has_entry or not has_exit:
                    status = "INSUFFICIENT_EXECUTION_CONTEXT"
                    reason = "recommendation_has_no_direction_entry_exit"
                elif bars_after < min_future_bars:
                    status = "INSUFFICIENT_FUTURE_BARS"
                    reason = "not_enough_market_bars_after_recommendation"
                else:
                    status = "READY_FOR_PAPER_EVALUATION"
                    reason = "paper_inputs_available"

                cur.execute(
                    """
                    INSERT INTO knowledge.paper_execution_validation_v1
                    (
                        recommendation_id,
                        symbol,
                        timeframe,
                        recommendation_code,
                        validation_status,
                        validation_reason,
                        bars_after_recommendation,
                        source_version,
                        evidence_json
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                    """,
                    (
                        rec["recommendation_id"],
                        rec["symbol"],
                        rec["timeframe"],
                        rec["recommendation_code"],
                        status,
                        reason,
                        bars_after,
                        SOURCE_VERSION,
                        json.dumps(
                            {
                                "recommendation_confidence": str(rec["recommendation_confidence"]),
                                "min_future_bars": min_future_bars,
                                "has_direction": has_direction,
                                "has_entry": has_entry,
                                "has_exit": has_exit,
                                "mode": "validation_only_no_orders_no_fills",
                            },
                            ensure_ascii=False,
                        ),
                    ),
                )
                inserted += 1

    print("=== PAPER_EXECUTION_VALIDATION_V1 ===")
    print(f"recommendations_validated={inserted}")
    print("mode=validation_only")
    print("paper_orders_created=0")
    print("paper_fills_created=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_EXECUTION_VALIDATION_V1_READY")


if __name__ == "__main__":
    main()
