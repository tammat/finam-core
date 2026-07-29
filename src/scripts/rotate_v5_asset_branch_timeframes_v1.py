from __future__ import annotations

import os
from datetime import timedelta

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
COOLDOWN = timedelta(minutes=30)


def choose_timeframe(current: str, counts: dict[str, int]) -> str:
    """Prefer the least observed branch; alternate ties to avoid starvation."""
    m1,m5 = int(counts.get("M1",0)),int(counts.get("M5",0))
    if m1 < m5:
        return "M1"
    if m5 < m1:
        return "M5"
    return "M1" if str(current).upper() == "M5" else "M5"


def main() -> int:
    switched = skipped_open = skipped_cooldown = 0
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT m.asset_code,m.symbol,m.scope_code,u.timeframe,
                       r.last_switched_at
                FROM analytics.v5_asset_scope_map_v1 m
                JOIN runtime_active_universe u ON u.symbol=m.symbol AND u.is_enabled
                LEFT JOIN analytics.v5_asset_branch_rotation_v1 r ON r.asset_code=m.asset_code
                WHERE m.enabled ORDER BY m.asset_code
            """)
            for row in cursor.fetchall():
                cursor.execute("""
                    SELECT EXISTS(
                      SELECT 1 FROM analytics.paper_research_position_projection_v1 p
                      WHERE p.portfolio_scope=%s AND p.symbol=%s
                        AND abs(coalesce(nullif(p.state->>'qty','')::numeric,0))>1e-9
                    ) AS has_position
                """,(row["scope_code"],row["symbol"]))
                if bool(cursor.fetchone()["has_position"]):
                    skipped_open += 1
                    continue
                last_switched = row.get("last_switched_at")
                cursor.execute("SELECT clock_timestamp() AS now")
                now = cursor.fetchone()["now"]
                if last_switched and now-last_switched < COOLDOWN:
                    skipped_cooldown += 1
                    continue
                cursor.execute("""
                    SELECT timeframe_code,sum(closed_trades)::int AS trades
                    FROM analytics.hierarchical_evidence_v1
                    WHERE cohort_code='FRESH_V5_CONFIRM' AND level_code='EXACT_CONTEXT'
                      AND scope_code=%s AND symbol_code=%s
                    GROUP BY timeframe_code
                """,(row["scope_code"],row["symbol"]))
                counts={str(item["timeframe_code"]):int(item["trades"] or 0)
                        for item in cursor.fetchall()}
                current=str(row.get("timeframe") or "M5").upper()
                selected=choose_timeframe(current,counts)
                cursor.execute("""
                    UPDATE runtime_active_universe
                    SET timeframe=%s,updated_at=clock_timestamp(),
                        raw_json=coalesce(raw_json,'{}'::jsonb)||jsonb_build_object(
                          'v5_asset_branch_timeframe',%s,
                          'v5_asset_branch_reason','LEAST_OBSERVED_FLAT_BRANCH')
                    WHERE symbol=%s AND is_enabled
                """,(selected,selected,row["symbol"]))
                cursor.execute("""
                    INSERT INTO analytics.v5_asset_branch_rotation_v1(
                      asset_code,symbol,previous_timeframe,selected_timeframe,
                      reason_code,last_switched_at,updated_at)
                    VALUES(%s,%s,%s,%s,'LEAST_OBSERVED_FLAT_BRANCH',clock_timestamp(),clock_timestamp())
                    ON CONFLICT(asset_code) DO UPDATE SET
                      symbol=excluded.symbol,previous_timeframe=excluded.previous_timeframe,
                      selected_timeframe=excluded.selected_timeframe,
                      reason_code=excluded.reason_code,last_switched_at=excluded.last_switched_at,
                      updated_at=excluded.updated_at
                """,(row["asset_code"],row["symbol"],current,selected))
                switched += 1
    print(f"switched={switched} skipped_open={skipped_open} skipped_cooldown={skipped_cooldown}")
    print("execution_changed=0 orders_changed=0 fills_changed=0 real_allowed=0")
    print("VERDICT=V5_ASSET_BRANCH_TIMEFRAME_ROTATION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
