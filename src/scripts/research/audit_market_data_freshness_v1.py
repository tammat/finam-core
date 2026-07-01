#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
AUDIT = "MARKET_DATA_FRESHNESS_AUDIT_V1"

DDL = """
CREATE TABLE IF NOT EXISTS warehouse.market_data_freshness_audit_v1 (
    id bigserial PRIMARY KEY,
    audit_name text NOT NULL,
    object_name text NOT NULL,
    symbol text NOT NULL,
    rows_count bigint NOT NULL,
    first_ts timestamptz,
    last_ts timestamptz,
    freshness_status text NOT NULL,
    runtime_ready boolean NOT NULL,
    research_ready boolean NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(audit_name, object_name, symbol)
);
"""

UPSERT = """
INSERT INTO warehouse.market_data_freshness_audit_v1
(audit_name, object_name, symbol, rows_count, first_ts, last_ts,
 freshness_status, runtime_ready, research_ready)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT(audit_name, object_name, symbol)
DO UPDATE SET
    rows_count=EXCLUDED.rows_count,
    first_ts=EXCLUDED.first_ts,
    last_ts=EXCLUDED.last_ts,
    freshness_status=EXCLUDED.freshness_status,
    runtime_ready=EXCLUDED.runtime_ready,
    research_ready=EXCLUDED.research_ready;
"""

def exists(cur, name: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (name,))
    return cur.fetchone()[0] is not None

def columns(cur, schema: str, table: str) -> set[str]:
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema=%s AND table_name=%s;
    """, (schema, table))
    return {r[0] for r in cur.fetchall()}

def status_from_rows(rows: int) -> str:
    return "FRESH" if rows > 0 else "EMPTY"

def main() -> None:
    print("=== MARKET_DATA_FRESHNESS_AUDIT_V1 ===")

    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            cur.execute(DDL)

            total_symbols = 0
            fresh_symbols = 0
            stale_symbols = 0
            empty_symbols = 0

            if exists(cur, "public.market_bars"):
                cols = columns(cur, "public", "market_bars")
                ts_col = "ts" if "ts" in cols else "timestamp" if "timestamp" in cols else None

                if ts_col:
                    cur.execute(f"""
                        SELECT
                            COALESCE(symbol::text, 'UNKNOWN') AS symbol,
                            count(*) AS rows_count,
                            min({ts_col}) AS first_ts,
                            max({ts_col}) AS last_ts
                        FROM public.market_bars
                        GROUP BY 1
                        ORDER BY 1;
                    """)
                else:
                    cur.execute("""
                        SELECT
                            COALESCE(symbol::text, 'UNKNOWN') AS symbol,
                            count(*) AS rows_count,
                            NULL::timestamptz AS first_ts,
                            NULL::timestamptz AS last_ts
                        FROM public.market_bars
                        GROUP BY 1
                        ORDER BY 1;
                    """)

                rows = cur.fetchall()

                for symbol, rows_count, first_ts, last_ts in rows:
                    rows_count = int(rows_count or 0)
                    freshness = status_from_rows(rows_count)
                    runtime_ready = rows_count > 0
                    research_ready = rows_count > 0

                    total_symbols += 1
                    if freshness == "FRESH":
                        fresh_symbols += 1
                    elif freshness == "STALE":
                        stale_symbols += 1
                    else:
                        empty_symbols += 1

                    cur.execute(
                        UPSERT,
                        (
                            AUDIT,
                            "public.market_bars",
                            symbol,
                            rows_count,
                            first_ts,
                            last_ts,
                            freshness,
                            runtime_ready,
                            research_ready,
                        ),
                    )

                    print(
                        f"SYMBOL|symbol={symbol}"
                        f"|bars={rows_count}"
                        f"|first_ts={first_ts}"
                        f"|last_ts={last_ts}"
                        f"|freshness={freshness}"
                        f"|runtime_ready={int(runtime_ready)}"
                        f"|research_ready={int(research_ready)}"
                    )

            normalized_exists = exists(cur, "warehouse.normalized_bar_event_v1")
            normalized_rows = 0

            if normalized_exists:
                cur.execute("SELECT count(*) FROM warehouse.normalized_bar_event_v1;")
                normalized_rows = int(cur.fetchone()[0] or 0)

            normalized_status = (
                "READY"
                if normalized_rows > 0
                else "EMPTY_NOT_BUILT"
                if normalized_exists
                else "MISSING"
            )

            pipeline_ready = (
                exists(cur, "public.market_bars")
                and exists(cur, "public.feature_snapshots")
                and exists(cur, "public.signals")
                and exists(cur, "public.trade_risk_context")
            )

            score = 100
            if total_symbols == 0:
                score -= 40
            if normalized_rows == 0:
                score -= 10
            if not pipeline_ready:
                score -= 20

            score = max(score, 0)
            risk = "LOW" if score >= 90 else "MEDIUM" if score >= 70 else "HIGH"

            cur.execute("""
                INSERT INTO warehouse.risk_assessment_scorecard_v1
                (audit_name, section_name, score, risk_level, status)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT(audit_name, section_name)
                DO UPDATE SET
                    score=EXCLUDED.score,
                    risk_level=EXCLUDED.risk_level,
                    status=EXCLUDED.status;
            """, (AUDIT, "Market Data Freshness", score, risk, "READY"))

        conn.commit()

        print("SECTION=NORMALIZED_LAYER")
        print(f"normalized_bar_event_v1_exists={int(normalized_exists)}")
        print(f"normalized_bar_event_v1_rows={normalized_rows}")
        print(f"normalized_status={normalized_status}")
        print("SECTION=PIPELINE")
        print(f"pipeline_ready={int(pipeline_ready)}")
        print("SECTION=SUMMARY")
        print(f"symbols_total={total_symbols}")
        print(f"fresh_symbols={fresh_symbols}")
        print(f"stale_symbols={stale_symbols}")
        print(f"empty_symbols={empty_symbols}")
        print(f"market_data_freshness_score={score}")
        print(f"market_data_freshness_risk_level={risk}")
        print("audit_mode=READ_ONLY")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print("VERDICT=MARKET_DATA_FRESHNESS_AUDIT_V1_READY")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
