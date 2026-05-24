from __future__ import annotations

import argparse
import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


EXCLUDED_SESSIONS = {"CLOSED", "WEEKEND", "UNKNOWN_SESSION"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-trades", type=int, default=15)
    parser.add_argument("--min-pf", type=float, default=1.3)
    parser.add_argument("--min-expectancy", type=float, default=0.0)
    args = parser.parse_args()

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ng_runtime_regime_policy_v2 (
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
                SELECT
                    symbol,
                    strategy,
                    timeframe,
                    session_bucket,
                    regime_v2,
                    trades,
                    profit_factor,
                    expectancy,
                    winrate
                FROM ng_regime_v2_trade_analytics
            """)

            saved = 0
            allowed = 0

            for row in cur.fetchall():
                symbol, strategy, timeframe, session_bucket, regime_v2, trades, pf, exp, winrate = row

                trades_i = int(trades or 0)
                pf_f = float(pf or 0)
                exp_f = float(exp or 0)
                winrate_f = float(winrate or 0)

                excluded = session_bucket in EXCLUDED_SESSIONS

                allow = (
                    not excluded
                    and trades_i >= args.min_trades
                    and pf_f >= args.min_pf
                    and exp_f > args.min_expectancy
                )

                reason = (
                    f"session={session_bucket} regime_v2={regime_v2} "
                    f"trades={trades_i} pf={round(pf_f, 4)} "
                    f"expectancy={round(exp_f, 6)} winrate={round(winrate_f, 4)} "
                    f"excluded_session={excluded} "
                    f"thresholds=min_trades:{args.min_trades},min_pf:{args.min_pf},min_expectancy:{args.min_expectancy}"
                )

                cur.execute("""
                    INSERT INTO ng_runtime_regime_policy_v2 (
                        symbol, strategy, timeframe,
                        session_bucket, regime_v2,
                        allow_runtime,
                        trades, profit_factor, expectancy, winrate,
                        reason, calculated_at
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
                    symbol, strategy, timeframe,
                    session_bucket, regime_v2,
                    allow,
                    trades_i, pf_f, exp_f, winrate_f,
                    reason,
                ))

                print(
                    "NG_RUNTIME_REGIME_POLICY_V2 "
                    f"symbol={symbol} session={session_bucket} regime_v2={regime_v2} "
                    f"allow={allow} reason={reason}",
                    flush=True,
                )

                saved += 1
                if allow:
                    allowed += 1

        conn.commit()

    print(
        f"NG_RUNTIME_REGIME_POLICY_V2_SUMMARY saved={saved} allowed={allowed}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
