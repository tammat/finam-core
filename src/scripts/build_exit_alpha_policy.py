from __future__ import annotations

import argparse
import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.exit_alpha_policy import build_exit_alpha_policy


def migrate() -> None:
    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS strategy_exit_alpha_policy (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    trade_source TEXT NOT NULL DEFAULT 'paper',
                    policy_name TEXT NOT NULL,
                    stop_atr NUMERIC NOT NULL,
                    take_atr NUMERIC NOT NULL,
                    trail_atr NUMERIC NOT NULL,
                    max_bars_held INTEGER NOT NULL,
                    reason TEXT NOT NULL DEFAULT '',
                    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, strategy, timeframe, trade_source)
                );
            """)
        conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--trade-source", default="paper")
    args = parser.parse_args()

    migrate()

    saved = 0

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.symbol, s.strategy, s.timeframe, s.trade_source,
                       s.profit_factor, s.expectancy,
                       COALESCE(g.volatility_state, 'unknown') AS volatility_state
                FROM strategy_statistics_v2 s
                LEFT JOIN futures_regime_governance g
                  ON g.symbol = s.symbol
                WHERE s.symbol = %s
                  AND s.trade_source = %s
            """, (args.symbol, args.trade_source))

            rows = cur.fetchall()

            for row in rows:
                symbol, strategy, timeframe, source, pf, expectancy, vol = row

                policy = build_exit_alpha_policy(
                    strategy=strategy,
                    timeframe=timeframe,
                    profit_factor=float(pf or 0),
                    expectancy=float(expectancy or 0),
                    volatility_state=str(vol or "unknown"),
                )

                reason = (
                    f"pf={pf} expectancy={expectancy} "
                    f"volatility={vol}"
                )

                cur.execute("""
                    INSERT INTO strategy_exit_alpha_policy (
                        symbol, strategy, timeframe, trade_source,
                        policy_name, stop_atr, take_atr, trail_atr,
                        max_bars_held, reason, calculated_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                    ON CONFLICT (symbol, strategy, timeframe, trade_source)
                    DO UPDATE SET
                        policy_name = EXCLUDED.policy_name,
                        stop_atr = EXCLUDED.stop_atr,
                        take_atr = EXCLUDED.take_atr,
                        trail_atr = EXCLUDED.trail_atr,
                        max_bars_held = EXCLUDED.max_bars_held,
                        reason = EXCLUDED.reason,
                        calculated_at = now()
                """, (
                    symbol,
                    policy.strategy,
                    policy.timeframe,
                    source,
                    policy.policy_name,
                    policy.stop_atr,
                    policy.take_atr,
                    policy.trail_atr,
                    policy.max_bars_held,
                    reason,
                ))

                saved += 1

                print(
                    "EXIT_ALPHA_POLICY "
                    f"symbol={symbol} strategy={policy.strategy} timeframe={policy.timeframe} "
                    f"policy={policy.policy_name} stop_atr={policy.stop_atr} "
                    f"take_atr={policy.take_atr} trail_atr={policy.trail_atr} "
                    f"max_bars_held={policy.max_bars_held}",
                    flush=True,
                )

        conn.commit()

    print(f"EXIT_ALPHA_POLICY_SUMMARY symbol={args.symbol} saved={saved}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
