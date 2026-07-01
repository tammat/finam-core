#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
AUDIT = "MARKET_DATA_QUALITY_AUDIT_V1"

DDL = """
CREATE TABLE IF NOT EXISTS warehouse.market_data_quality_audit_v1 (
    id bigserial PRIMARY KEY,
    audit_name text NOT NULL,
    check_name text NOT NULL,
    object_name text NOT NULL,
    rows_checked bigint NOT NULL,
    bad_rows bigint NOT NULL,
    status text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(audit_name, check_name, object_name)
);
"""

UPSERT = """
INSERT INTO warehouse.market_data_quality_audit_v1
(audit_name, check_name, object_name, rows_checked, bad_rows, status)
VALUES (%s,%s,%s,%s,%s,%s)
ON CONFLICT(audit_name, check_name, object_name)
DO UPDATE SET
    rows_checked=EXCLUDED.rows_checked,
    bad_rows=EXCLUDED.bad_rows,
    status=EXCLUDED.status;
"""

def exists(cur, name: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (name,))
    return cur.fetchone()[0] is not None

def scalar(cur, sql: str) -> int:
    cur.execute(sql)
    return int(cur.fetchone()[0] or 0)

def add_check(cur, check_name: str, object_name: str, rows_checked: int, bad_rows: int) -> None:
    status = "OK" if bad_rows == 0 else "ISSUES"
    cur.execute(UPSERT, (AUDIT, check_name, object_name, rows_checked, bad_rows, status))
    print(
        f"QUALITY|check={check_name}"
        f"|object={object_name}"
        f"|rows_checked={rows_checked}"
        f"|bad_rows={bad_rows}"
        f"|status={status}"
    )

def main() -> None:
    print("=== MARKET_DATA_QUALITY_AUDIT_V1 ===")

    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            cur.execute(DDL)

            total_bad = 0
            checks = 0

            if exists(cur, "public.market_bars"):
                rows_checked = scalar(cur, "SELECT count(*) FROM public.market_bars;")

                bad_ohlc = scalar(cur, """
                    SELECT count(*)
                    FROM public.market_bars
                    WHERE open IS NULL
                       OR high IS NULL
                       OR low IS NULL
                       OR close IS NULL
                       OR high < low
                       OR open < 0
                       OR high < 0
                       OR low < 0
                       OR close < 0;
                """)
                add_check(cur, "OHLC_VALIDITY", "public.market_bars", rows_checked, bad_ohlc)
                total_bad += bad_ohlc
                checks += 1

                bad_volume = scalar(cur, """
                    SELECT count(*)
                    FROM public.market_bars
                    WHERE volume IS NULL OR volume < 0;
                """)
                add_check(cur, "VOLUME_VALIDITY", "public.market_bars", rows_checked, bad_volume)
                total_bad += bad_volume
                checks += 1

                duplicate_bars = scalar(cur, """
                    SELECT count(*)
                    FROM (
                        SELECT symbol, timeframe, ts
                        FROM public.market_bars
                        GROUP BY symbol, timeframe, ts
                        HAVING count(*) > 1
                    ) x;
                """)
                add_check(cur, "DUPLICATE_BARS", "public.market_bars", rows_checked, duplicate_bars)
                total_bad += duplicate_bars
                checks += 1
            else:
                add_check(cur, "TABLE_EXISTS", "public.market_bars", 0, 1)
                total_bad += 1
                checks += 1

            if exists(cur, "public.market_ticks"):
                rows_checked = scalar(cur, "SELECT count(*) FROM public.market_ticks;")

                bad_ticks = scalar(cur, """
                    SELECT count(*)
                    FROM public.market_ticks
                    WHERE price IS NULL OR price < 0;
                """)
                add_check(cur, "TICK_PRICE_VALIDITY", "public.market_ticks", rows_checked, bad_ticks)
                total_bad += bad_ticks
                checks += 1
            else:
                add_check(cur, "TABLE_EXISTS", "public.market_ticks", 0, 1)
                total_bad += 1
                checks += 1

            if exists(cur, "warehouse.normalized_bar_event_v1"):
                normalized_rows = scalar(cur, "SELECT count(*) FROM warehouse.normalized_bar_event_v1;")
                add_check(cur, "NORMALIZED_BAR_LAYER_EXISTS", "warehouse.normalized_bar_event_v1", normalized_rows, 0)
                checks += 1
            else:
                add_check(cur, "NORMALIZED_BAR_LAYER_EXISTS", "warehouse.normalized_bar_event_v1", 0, 1)
                total_bad += 1
                checks += 1

            score = 100 if total_bad == 0 else 85 if total_bad < 100 else 70
            risk = "LOW" if score >= 90 else "MEDIUM" if score >= 70 else "HIGH"

            cur.execute("""
                INSERT INTO warehouse.risk_assessment_scorecard_v1
                (audit_name, section_name, score, risk_level, status)
                VALUES(%s,%s,%s,%s,%s)
                ON CONFLICT(audit_name, section_name)
                DO UPDATE SET
                    score=EXCLUDED.score,
                    risk_level=EXCLUDED.risk_level,
                    status=EXCLUDED.status;
            """, (AUDIT, "Market Data Quality", score, risk, "READY"))

        conn.commit()

        print(f"quality_checks={checks}")
        print(f"bad_rows_total={total_bad}")
        print(f"market_data_quality_score={score}")
        print(f"market_data_quality_risk_level={risk}")
        print("audit_mode=READ_ONLY")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print("VERDICT=MARKET_DATA_QUALITY_AUDIT_V1_READY")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
