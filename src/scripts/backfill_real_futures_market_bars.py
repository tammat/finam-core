from __future__ import annotations

import argparse
import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.data.finam_futures_candles_provider import (
    FinamFuturesCandlesProvider,
)


def load_contracts(roots: list[str], max_contracts: int) -> list[str]:
    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT contract_symbol
                FROM futures_contract_universe
                WHERE root_symbol = ANY(%s)
                  AND is_active = TRUE
                  AND status <> 'QUARANTINE'
                ORDER BY root_symbol, roll_priority, expiration_date NULLS LAST
                """,
                (roots,),
            )

            rows = cur.fetchall()

    return [row[0] for row in rows[: max_contracts * len(roots)]]


def save_market_bars(
    *,
    symbol: str,
    timeframe: str,
    candles: list[dict],
) -> int:
    rows = [
        (
            symbol,
            timeframe,
            x["ts"],
            x["open"],
            x["high"],
            x["low"],
            x["close"],
            x["volume"],
        )
        for x in candles
    ]

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO market_bars (
                    symbol,
                    timeframe,
                    ts,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    source
                )
                VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,
                    'moex_iss_futures_v1'
                )
                ON CONFLICT (symbol, timeframe, ts)
                DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    source = EXCLUDED.source
                """,
                rows,
            )

        conn.commit()

    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--roots", default="BR,NG,USD")
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--bars", type=int, default=120)
    parser.add_argument("--max-contracts", type=int, default=3)
    args = parser.parse_args()

    roots = [x.strip() for x in args.roots.split(",") if x.strip()]

    provider = FinamFuturesCandlesProvider()

    symbols = load_contracts(roots, args.max_contracts)

    total = 0

    for symbol in symbols:
        candles = provider.load_candles(
            symbol=symbol,
            interval=5,
            limit=args.bars,
        )

        inserted = save_market_bars(
            symbol=symbol,
            timeframe=args.timeframe,
            candles=candles,
        )

        total += inserted

        print(
            "REAL_FUTURES_MARKET_BARS_OK "
            f"symbol={symbol} "
            f"timeframe={args.timeframe} "
            f"bars={inserted}",
            flush=True,
        )

    print(
        "REAL_FUTURES_MARKET_BARS_SUMMARY "
        f"symbols={len(symbols)} bars={total}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
