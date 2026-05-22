from __future__ import annotations

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


def main() -> int:
    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS strategy_exit_alpha_radar (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    trade_source TEXT NOT NULL,
                    policy_name TEXT NOT NULL,
                    radar_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    runtime_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                    reason TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, strategy, timeframe, trade_source)
                );
            """)

            cur.execute("""
                INSERT INTO strategy_exit_alpha_radar (
                    symbol, strategy, timeframe, trade_source,
                    policy_name, radar_enabled, runtime_enabled, reason, created_at
                )
                SELECT symbol, strategy, timeframe, trade_source,
                       policy_name, TRUE, FALSE, reason, now()
                FROM strategy_best_exit_alpha_policy
                WHERE status='RADAR_EXIT_ALPHA_CANDIDATE'
                ON CONFLICT (symbol, strategy, timeframe, trade_source)
                DO UPDATE SET
                    policy_name=EXCLUDED.policy_name,
                    radar_enabled=TRUE,
                    runtime_enabled=FALSE,
                    reason=EXCLUDED.reason,
                    created_at=now()
            """)

            saved = cur.rowcount or 0

        conn.commit()

    print(f"EXIT_ALPHA_RADAR_SYNC_OK rows={saved}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
