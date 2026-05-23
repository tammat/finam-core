from __future__ import annotations

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


def main() -> int:
    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS runtime_observations (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    runtime_state TEXT,
                    active_edge BOOLEAN,
                    market_data_fresh BOOLEAN,
                    session_bucket TEXT,
                    regime_v2 TEXT,
                    governance_decision TEXT,
                    allow_runtime BOOLEAN,
                    last_bar_ts TIMESTAMPTZ,
                    bar_age_min NUMERIC,
                    reason TEXT,
                    observed_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );

                CREATE INDEX IF NOT EXISTS idx_runtime_observations_symbol_time
                ON runtime_observations(symbol, observed_at DESC);

                CREATE INDEX IF NOT EXISTS idx_runtime_observations_strategy_time
                ON runtime_observations(strategy, timeframe, observed_at DESC);
            """)

            cur.execute("""
                INSERT INTO runtime_observations (
                    symbol, strategy, timeframe,
                    runtime_state,
                    active_edge,
                    market_data_fresh,
                    session_bucket,
                    regime_v2,
                    governance_decision,
                    allow_runtime,
                    last_bar_ts,
                    bar_age_min,
                    reason,
                    observed_at
                )
                SELECT
                    u.symbol,
                    u.strategy,
                    u.timeframe,
                    s.runtime_state,
                    e.active_edge,
                    s.market_data_fresh,
                    e.current_session,
                    e.required_regime_v2,
                    e.governance_decision,
                    e.governance_allow_runtime,
                    mb.last_bar_ts,
                    round(extract(epoch from (now() - mb.last_bar_ts)) / 60, 2),
                    COALESCE(s.state_reason, e.reason, u.disable_reason),
                    now()
                FROM runtime_active_universe u
                LEFT JOIN ng_live_runtime_state s
                  ON s.symbol=u.symbol
                 AND s.strategy=u.strategy
                 AND s.timeframe=u.timeframe
                LEFT JOIN ng_active_edge_state e
                  ON e.symbol=u.symbol
                 AND e.strategy=u.strategy
                 AND e.timeframe=u.timeframe
                LEFT JOIN LATERAL (
                    SELECT max(ts) AS last_bar_ts
                    FROM market_bars b
                    WHERE b.symbol=u.symbol
                      AND b.timeframe=u.timeframe
                ) mb ON TRUE
                WHERE u.symbol IS NOT NULL
            """)

            saved = cur.rowcount or 0

        conn.commit()

    print(f"RUNTIME_OBSERVATIONS_COLLECTED saved={saved}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
