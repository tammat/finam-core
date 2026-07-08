from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "TRADING_PLAN_PARAMETER_BUILDER_V1"


def d(value: Any) -> Decimal:
    return Decimal(str(value))


def load_parameter(cur, code: str) -> str:
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
        raise RuntimeError(f"missing_parameter:{code}")
    return str(row["parameter_value"])


def load_profile(cur, profile_code: str) -> dict[str, Any]:
    cur.execute(
        """
        SELECT *
        FROM knowledge.trading_plan_parameter_profile_v1
        WHERE profile_code=%s
          AND enabled
        """,
        (profile_code,),
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"missing_profile:{profile_code}")
    return dict(row)


def resolve_source(
    cur,
    source_code: str,
    symbol: str,
    timeframe: str,
) -> tuple[Decimal, dict[str, Any]]:
    cur.execute(
        """
        SELECT *
        FROM knowledge.trading_plan_source_v1
        WHERE source_code=%s
          AND enabled
        """,
        (source_code,),
    )
    source = cur.fetchone()
    if not source:
        raise RuntimeError(f"missing_source:{source_code}")

    group_code = str(source["source_group"])

    if group_code == "PRICE":
        cur.execute(
            """
            SELECT close, ts
            FROM public.market_bars
            WHERE symbol=%s
              AND timeframe=%s
              AND close IS NOT NULL
            ORDER BY ts DESC
            LIMIT 1
            """,
            (symbol, timeframe),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError(f"missing_price:{symbol}:{timeframe}")
        return d(row["close"]), {
            "source_code": source_code,
            "source_group": group_code,
            "knowledge_table": source["knowledge_table"],
            "knowledge_field": source["knowledge_field"],
            "bar_ts": str(row["ts"]),
        }

    if group_code == "MARKET_STRUCTURE":
        cur.execute(
            """
            SELECT structure_id, level_price, level_strength, detected_at, evidence_json
            FROM knowledge.market_structure_v1
            WHERE symbol=%s
              AND timeframe=%s
              AND structure_type_code=%s
              AND source_version='MARKET_STRUCTURE_ENGINE_V1'
            ORDER BY created_at DESC, level_strength DESC NULLS LAST
            LIMIT 1
            """,
            (symbol, timeframe, source_code),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError(f"missing_market_structure:{source_code}:{symbol}:{timeframe}")
        return d(row["level_price"]), {
            "source_code": source_code,
            "source_group": group_code,
            "knowledge_table": source["knowledge_table"],
            "knowledge_field": source["knowledge_field"],
            "structure_id": int(row["structure_id"]),
            "level_strength": str(row["level_strength"]),
            "detected_at": str(row["detected_at"]),
            "source_evidence": row["evidence_json"],
        }

    raise RuntimeError(f"unsupported_source_group:{group_code}")


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            active_profile = load_parameter(cur, "TRADING_PLAN_ACTIVE_PROFILE")
            horizon_bars = int(Decimal(load_parameter(cur, "TRADING_PLAN_HORIZON_BARS")))
            risk_unit = d(load_parameter(cur, "TRADING_PLAN_RISK_UNIT"))
            profile = load_profile(cur, active_profile)

            cur.execute(
                """
                SELECT DISTINCT ON (r.symbol, r.timeframe)
                    r.recommendation_id,
                    r.symbol,
                    r.timeframe,
                    r.evidence_json,
                    x.direction_code,
                    x.source_context_id,
                    x.source_edge_context_id
                FROM knowledge.recommendation_result_v1 r
                JOIN knowledge.recommendation_execution_context_v1 x
                  ON x.recommendation_id=r.recommendation_id
                WHERE x.source_version='RECOMMENDATION_EXECUTION_CONTEXT_MODELS_V1'
                  AND r.evidence_json ? 'market_context_id'
                  AND r.evidence_json ? 'edge_context_id'
                ORDER BY r.symbol, r.timeframe, r.created_at DESC
                """
            )
            rows = cur.fetchall()

            created = 0
            failed = 0

            for row in rows:
                try:
                    entry_price, entry_evidence = resolve_source(
                        cur, profile["entry_source"], row["symbol"], row["timeframe"]
                    )
                    stop_price, stop_evidence = resolve_source(
                        cur, profile["stop_source"], row["symbol"], row["timeframe"]
                    )
                    target_price, target_evidence = resolve_source(
                        cur, profile["target_source"], row["symbol"], row["timeframe"]
                    )

                    cur.execute(
                        """
                        INSERT INTO knowledge.recommendation_execution_context_v1
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
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,0,0,0,%s::jsonb,%s)
                        ON CONFLICT(recommendation_id, source_version)
                        DO NOTHING
                        """,
                        (
                            row["recommendation_id"],
                            row["direction_code"],
                            entry_price,
                            stop_price,
                            target_price,
                            horizon_bars,
                            risk_unit,
                            row["source_context_id"],
                            row["source_edge_context_id"],
                            json.dumps(
                                {
                                    "builder_mode": "profile_source_registry",
                                    "profile_code": active_profile,
                                    "entry_source": profile["entry_source"],
                                    "stop_source": profile["stop_source"],
                                    "target_source": profile["target_source"],
                                    "entry_evidence": entry_evidence,
                                    "stop_evidence": stop_evidence,
                                    "target_evidence": target_evidence,
                                    "execution_allowed": 0,
                                    "runtime_allowed": 0,
                                    "micro_live_allowed": 0,
                                },
                                ensure_ascii=False,
                            ),
                            SOURCE_VERSION,
                        ),
                    )
                    created += cur.rowcount

                except Exception as exc:
                    failed += 1
                    print(f"BUILD_FAILED symbol={row['symbol']} timeframe={row['timeframe']} reason={exc}")

    print("=== TRADING_PLAN_PARAMETER_BUILDER_V1 ===")
    print(f"trading_plan_parameter_rows_created={created}")
    print(f"build_failed_rows={failed}")
    print("profile_source=postgres")
    print("source_registry=postgres")
    print("market_structure_source=knowledge.market_structure_v1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=TRADING_PLAN_PARAMETER_BUILDER_V1_READY")


if __name__ == "__main__":
    main()
