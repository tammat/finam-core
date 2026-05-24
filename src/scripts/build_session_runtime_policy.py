from __future__ import annotations

import argparse
import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-trades", type=int, default=10)
    parser.add_argument("--min-pf", type=float, default=1.3)
    parser.add_argument("--min-expectancy", type=float, default=0.0)
    args = parser.parse_args()

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS session_runtime_policy (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    trade_source TEXT NOT NULL,
                    session_bucket TEXT NOT NULL,
                    allow_runtime BOOLEAN NOT NULL,
                    reason TEXT NOT NULL,
                    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, strategy, timeframe, trade_source, session_bucket)
                );
            """)

            cur.execute("""
                SELECT symbol, strategy, timeframe, trade_source,
                       session_bucket, trades, profit_factor, expectancy
                FROM futures_session_trade_analytics
            """)

            saved = 0

            for symbol, strategy, timeframe, trade_source, bucket, trades, pf, exp in cur.fetchall():
                allow = (
                    int(trades or 0) >= args.min_trades
                    and float(pf or 0) >= args.min_pf
                    and float(exp or 0) > args.min_expectancy
                )

                reason = (
                    f"session={bucket} trades={trades} "
                    f"pf={round(float(pf or 0), 4)} expectancy={round(float(exp or 0), 6)}"
                )

                cur.execute("""
                    INSERT INTO session_runtime_policy (
                        symbol, strategy, timeframe, trade_source,
                        session_bucket, allow_runtime, reason, calculated_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,now())
                    ON CONFLICT (symbol, strategy, timeframe, trade_source, session_bucket)
                    DO UPDATE SET
                        allow_runtime=EXCLUDED.allow_runtime,
                        reason=EXCLUDED.reason,
                        calculated_at=now()
                """, (
                    symbol, strategy, timeframe, trade_source,
                    bucket, allow, reason,
                ))

                print(
                    "SESSION_RUNTIME_POLICY "
                    f"symbol={symbol} strategy={strategy} timeframe={timeframe} "
                    f"session={bucket} allow={allow} reason={reason}",
                    flush=True,
                )
                saved += 1

        conn.commit()

    print(f"SESSION_RUNTIME_POLICY_SUMMARY saved={saved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
