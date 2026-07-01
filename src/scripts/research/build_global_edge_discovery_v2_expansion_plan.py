from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics_global_edge_expansion_plan_v2 (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    plan_key TEXT NOT NULL UNIQUE,
                    plan_status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    instruments_scope TEXT NOT NULL,
                    timeframes_scope TEXT NOT NULL,
                    strategies_scope TEXT NOT NULL,
                    regimes_scope TEXT NOT NULL,
                    runtime_allowed BOOLEAN NOT NULL DEFAULT false,
                    execution_allowed BOOLEAN NOT NULL DEFAULT false,
                    micro_live_allowed BOOLEAN NOT NULL DEFAULT false
                );
            """)

            cur.execute("""
                INSERT INTO analytics_global_edge_expansion_plan_v2
                (
                    plan_key,
                    plan_status,
                    reason,
                    instruments_scope,
                    timeframes_scope,
                    strategies_scope,
                    regimes_scope,
                    runtime_allowed,
                    execution_allowed,
                    micro_live_allowed
                )
                VALUES (
                    'GLOBAL_EDGE_DISCOVERY_V2_EXPANSION_PLAN',
                    'READY',
                    'V2 found ranked candidates but all were rejected by robustness and walk-forward filters; futures and FX also lack replay data.',
                    'expand futures, equities, FX; repair BR/NG/Si/USDRUB bars mapping',
                    'M1,M5,M15,H1',
                    'BREAKOUT,MEAN_REVERSION,TREND_FOLLOWING,VOLATILITY_EXPANSION',
                    'trend,range,compression,high_volatility,low_volatility',
                    false,
                    false,
                    false
                )
                ON CONFLICT (plan_key)
                DO UPDATE SET
                    created_at = now(),
                    plan_status = EXCLUDED.plan_status,
                    reason = EXCLUDED.reason,
                    instruments_scope = EXCLUDED.instruments_scope,
                    timeframes_scope = EXCLUDED.timeframes_scope,
                    strategies_scope = EXCLUDED.strategies_scope,
                    regimes_scope = EXCLUDED.regimes_scope,
                    runtime_allowed = false,
                    execution_allowed = false,
                    micro_live_allowed = false;
            """)

    print("=== GLOBAL_EDGE_DISCOVERY_V2_EXPANSION_PLAN ===")
    print("mode=research_only")
    print("reason=ranked_candidates_failed_robustness_and_walk_forward")
    print("data_gap=futures_fx_no_replay_data")
    print("instruments_scope=expand_futures_equities_fx")
    print("timeframes_scope=M1,M5,M15,H1")
    print("strategies_scope=BREAKOUT,MEAN_REVERSION,TREND_FOLLOWING,VOLATILITY_EXPANSION")
    print("regimes_scope=trend,range,compression,high_volatility,low_volatility")
    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("next=MULTI_TIMEFRAME_UNIVERSE_EXPANSION_V1")
    print("VERDICT=GLOBAL_EDGE_DISCOVERY_V2_EXPANSION_PLAN_READY")


if __name__ == "__main__":
    main()
