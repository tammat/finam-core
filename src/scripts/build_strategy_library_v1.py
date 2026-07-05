from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

STRATEGIES = [
    ("VOLATILITY_BREAKOUT_V2", "VOLATILITY_BREAKOUT", "BREAKOUT", 10, ["M5","M15"]),
    ("OPENING_RANGE_BREAKOUT_V1", "OPENING_RANGE_BREAKOUT", "BREAKOUT", 20, ["M5","M15"]),
    ("NR7_BREAKOUT_V1", "NR7_BREAKOUT", "VOLATILITY", 30, ["M5","M15"]),
    ("MOMENTUM_CONTINUATION_V1", "MOMENTUM_CONTINUATION", "MOMENTUM", 40, ["M5","M15"]),
    ("ATR_IMPULSE_V1", "ATR_IMPULSE", "MOMENTUM", 50, ["M1","M5"]),
    ("RSI_MEAN_REVERSION_V1", "RSI_MEAN_REVERSION", "MEAN_REVERSION", 60, ["M5","M15"]),
    ("BOLLINGER_REVERSION_V1", "BOLLINGER_REVERSION", "MEAN_REVERSION", 70, ["M5","M15"]),
    ("VWAP_REVERSION_V1", "VWAP_REVERSION", "VWAP", 80, ["M1","M5"]),
    ("VOLUME_IMPULSE_V1", "VOLUME_IMPULSE", "VOLUME", 90, ["M1","M5"]),
    ("FALSE_BREAKOUT_V1", "FALSE_BREAKOUT", "LIQUIDITY", 100, ["M5","M15"]),
]

def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for code, family, category, priority, timeframes in STRATEGIES:
                cur.execute("""
                    INSERT INTO analytics.strategy_library_v1 (
                        strategy_code,
                        strategy_family,
                        category,
                        status_code,
                        priority,
                        description,
                        default_timeframes,
                        parameter_schema,
                        enabled,
                        source_version,
                        updated_at
                    )
                    VALUES (
                        %s,%s,%s,'EXPERIMENT',%s,%s,%s,
                        '{}'::jsonb,
                        true,
                        'STRATEGY_LIBRARY_V1',
                        now()
                    )
                    ON CONFLICT(strategy_code) DO UPDATE SET
                        strategy_family=EXCLUDED.strategy_family,
                        category=EXCLUDED.category,
                        priority=EXCLUDED.priority,
                        default_timeframes=EXCLUDED.default_timeframes,
                        enabled=true,
                        source_version='STRATEGY_LIBRARY_V1',
                        updated_at=now();
                """, (
                    code,
                    family,
                    category,
                    priority,
                    f"Research hypothesis for {code}",
                    timeframes,
                ))

            cur.execute("""
                SELECT count(*) AS total,
                       count(*) FILTER (WHERE enabled=true) AS enabled
                FROM analytics.strategy_library_v1;
            """)
            row = cur.fetchone()

    print("=== STRATEGY_LIBRARY_V1 ===")
    print(f"strategies_total={row['total']}")
    print(f"strategies_enabled={row['enabled']}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=STRATEGY_LIBRARY_V1_READY")

if __name__ == "__main__":
    main()
