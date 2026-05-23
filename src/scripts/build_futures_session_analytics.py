from __future__ import annotations

import argparse
import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.futures_session_classifier import classify_futures_session


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol-like", default="%@RTSX")
    args = parser.parse_args()

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS futures_session_trade_analytics (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    trade_source TEXT NOT NULL,
                    session_bucket TEXT NOT NULL,
                    trades INTEGER NOT NULL,
                    gross_profit NUMERIC NOT NULL,
                    gross_loss NUMERIC NOT NULL,
                    profit_factor NUMERIC NOT NULL,
                    expectancy NUMERIC NOT NULL,
                    winrate NUMERIC NOT NULL,
                    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, strategy, timeframe, trade_source, session_bucket)
                );
            """)

            cur.execute("""
                SELECT symbol, strategy, timeframe, trade_source,
                       entry_ts, pnl
                FROM closed_trade_chains_v2
                WHERE symbol LIKE %s
                  AND strategy IS NOT NULL
                  AND timeframe IS NOT NULL
            """, (args.symbol_like,))

            groups = {}

            for symbol, strategy, timeframe, trade_source, entry_ts, pnl in cur.fetchall():
                bucket = classify_futures_session(entry_ts)
                key = (symbol, strategy, timeframe, trade_source, bucket)
                groups.setdefault(key, []).append(float(pnl or 0.0))

            saved = 0

            for key, pnls in groups.items():
                symbol, strategy, timeframe, trade_source, bucket = key

                wins = [x for x in pnls if x > 0]
                losses = [x for x in pnls if x < 0]

                gross_profit = sum(wins)
                gross_loss = abs(sum(losses))
                pf = gross_profit / gross_loss if gross_loss else (gross_profit if gross_profit else 0.0)
                expectancy = sum(pnls) / len(pnls) if pnls else 0.0
                winrate = len(wins) / len(pnls) if pnls else 0.0

                cur.execute("""
                    INSERT INTO futures_session_trade_analytics (
                        symbol, strategy, timeframe, trade_source, session_bucket,
                        trades, gross_profit, gross_loss,
                        profit_factor, expectancy, winrate, calculated_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                    ON CONFLICT (symbol, strategy, timeframe, trade_source, session_bucket)
                    DO UPDATE SET
                        trades=EXCLUDED.trades,
                        gross_profit=EXCLUDED.gross_profit,
                        gross_loss=EXCLUDED.gross_loss,
                        profit_factor=EXCLUDED.profit_factor,
                        expectancy=EXCLUDED.expectancy,
                        winrate=EXCLUDED.winrate,
                        calculated_at=now()
                """, (
                    symbol, strategy, timeframe, trade_source, bucket,
                    len(pnls), gross_profit, gross_loss, pf, expectancy, winrate,
                ))

                print(
                    "FUTURES_SESSION_ANALYTICS "
                    f"symbol={symbol} strategy={strategy} tf={timeframe} "
                    f"session={bucket} trades={len(pnls)} pf={round(pf, 4)} "
                    f"expectancy={round(expectancy, 6)}",
                    flush=True,
                )

                saved += 1

        conn.commit()

    print(f"FUTURES_SESSION_ANALYTICS_SUMMARY saved={saved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
