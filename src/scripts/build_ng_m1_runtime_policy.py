from __future__ import annotations

import argparse
import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


EXCLUDED_SESSIONS = {"CLOSED", "WEEKEND", "UNKNOWN_SESSION"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-trades", type=int, default=30)
    parser.add_argument("--min-pf", type=float, default=1.3)
    parser.add_argument("--min-expectancy", type=float, default=0.0)
    args = parser.parse_args()

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ng_m1_runtime_policy (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    session_bucket TEXT NOT NULL,
                    regime_v2 TEXT NOT NULL,
                    allow_runtime BOOLEAN NOT NULL,
                    trades INTEGER NOT NULL,
                    profit_factor NUMERIC NOT NULL,
                    expectancy NUMERIC NOT NULL,
                    winrate NUMERIC NOT NULL,
                    reason TEXT NOT NULL,
                    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, strategy, timeframe, session_bucket, regime_v2)
                );
            """)

            cur.execute("""
                SELECT symbol, strategy, timeframe, session_bucket, regime_v2,
                       trades, profit_factor, expectancy, winrate
                FROM ng_m1_session_regime_matrix
            """)

            saved = 0
            allowed = 0

            for symbol, strategy, timeframe, session, regime, trades, pf, exp, wr in cur.fetchall():
                trades_i = int(trades or 0)
                pf_f = float(pf or 0)
                exp_f = float(exp or 0)
                wr_f = float(wr or 0)

                excluded = session in EXCLUDED_SESSIONS

                allow = (
                    not excluded
                    and trades_i >= args.min_trades
                    and pf_f >= args.min_pf
                    and exp_f > args.min_expectancy
                )

                reason = (
                    f"session={session} regime_v2={regime} trades={trades_i} "
                    f"pf={round(pf_f, 4)} expectancy={round(exp_f, 6)} "
                    f"winrate={round(wr_f, 4)} excluded_session={excluded}"
                )

                cur.execute("""
                    INSERT INTO ng_m1_runtime_policy (
                        symbol, strategy, timeframe, session_bucket, regime_v2,
                        allow_runtime, trades, profit_factor, expectancy,
                        winrate, reason, calculated_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                    ON CONFLICT(symbol, strategy, timeframe, session_bucket, regime_v2)
                    DO UPDATE SET
                        allow_runtime=EXCLUDED.allow_runtime,
                        trades=EXCLUDED.trades,
                        profit_factor=EXCLUDED.profit_factor,
                        expectancy=EXCLUDED.expectancy,
                        winrate=EXCLUDED.winrate,
                        reason=EXCLUDED.reason,
                        calculated_at=now()
                """, (
                    symbol, strategy, timeframe, session, regime,
                    allow, trades_i, pf_f, exp_f, wr_f, reason,
                ))

                print(
                    "NG_M1_RUNTIME_POLICY "
                    f"symbol={symbol} session={session} regime_v2={regime} "
                    f"allow={allow} reason={reason}",
                    flush=True,
                )

                saved += 1
                if allow:
                    allowed += 1

        conn.commit()

    print(f"NG_M1_RUNTIME_POLICY_SUMMARY saved={saved} allowed={allowed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
