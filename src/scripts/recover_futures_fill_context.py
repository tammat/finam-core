from __future__ import annotations

import argparse
import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


def infer_context(symbol: str) -> tuple[str, str]:
    if symbol.startswith("BR"):
        return "BR_CONSERVATIVE_BREAKOUT", "M5"
    if symbol.startswith("NG"):
        return "NG_CONSERVATIVE_SETUP", "M5"
    if symbol.startswith("USDRUB"):
        return "USD_INTRADAY_REGIME", "M5"
    return "", ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--trade-source", default="paper")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    symbols = [x.strip() for x in args.symbols.split(",") if x.strip()]

    total = 0

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                ALTER TABLE trades
                ADD COLUMN IF NOT EXISTS strategy TEXT NOT NULL DEFAULT '';

                ALTER TABLE trades
                ADD COLUMN IF NOT EXISTS timeframe TEXT NOT NULL DEFAULT '';
            """)

            for symbol in symbols:
                strategy, timeframe = infer_context(symbol)

                if not strategy:
                    print(f"FUTURES_FILL_CONTEXT_SKIP symbol={symbol} reason=no_rule")
                    continue

                cur.execute("""
                    UPDATE trades
                    SET strategy = %s,
                        timeframe = %s
                    WHERE symbol = %s
                      AND COALESCE(trade_source, '') = %s
                      AND COALESCE(is_invalid, FALSE) = FALSE
                      AND (
                            COALESCE(strategy, '') = ''
                         OR COALESCE(timeframe, '') = ''
                      )
                """, (strategy, timeframe, symbol, args.trade_source))

                changed = cur.rowcount or 0
                total += changed

                print(
                    "FUTURES_FILL_CONTEXT_RECOVERY "
                    f"symbol={symbol} strategy={strategy} timeframe={timeframe} updated={changed}",
                    flush=True,
                )

            if args.apply:
                conn.commit()
            else:
                conn.rollback()

    print(
        "FUTURES_FILL_CONTEXT_RECOVERY_SUMMARY "
        f"symbols={len(symbols)} updated={total} applied={args.apply}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
