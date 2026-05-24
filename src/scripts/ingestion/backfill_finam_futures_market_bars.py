from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

import psycopg
import grpc
import time

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.ingestion.bars_client import FinamBarsClient


def load_contracts(roots: list[str], max_contracts: int) -> list[str]:
    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT contract_symbol
                FROM futures_contract_universe
                WHERE root_symbol = ANY(%s)
                  AND is_active = TRUE
                  AND status <> 'QUARANTINE'
                ORDER BY root_symbol, roll_priority, expiration_date NULLS LAST
            """, (roots,))
            rows = cur.fetchall()

    result = []
    per_root = {}

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            for (symbol,) in rows:
                cur.execute("""
                    SELECT root_symbol
                    FROM futures_contract_universe
                    WHERE contract_symbol=%s
                """, (symbol,))
                root = cur.fetchone()[0]
                per_root[root] = per_root.get(root, 0) + 1
                if per_root[root] <= max_contracts:
                    result.append(symbol)

    return result


def migrate_market_bars() -> None:
    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS market_bars (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    ts TIMESTAMPTZ NOT NULL,
                    open NUMERIC NOT NULL,
                    high NUMERIC NOT NULL,
                    low NUMERIC NOT NULL,
                    close NUMERIC NOT NULL,
                    volume NUMERIC NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, timeframe, ts)
                );

                ALTER TABLE market_bars
                ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'unknown';

                CREATE INDEX IF NOT EXISTS idx_market_bars_symbol_tf_ts
                ON market_bars(symbol, timeframe, ts DESC);
            """)
        conn.commit()


def _num(v) -> float:
    if hasattr(v, "value"):
        return float(v.value)
    return float(v)


def _bar_ts(bar) -> datetime:
    ts = getattr(bar, "timestamp", None) or getattr(bar, "time", None)
    if hasattr(ts, "ToDatetime"):
        return ts.ToDatetime().replace(tzinfo=timezone.utc)
    raise ValueError(f"Unsupported bar timestamp: {bar!r}")


def save_bars(symbol: str, timeframe: str, bars) -> int:
    rows = []

    for b in bars:
        rows.append((
            symbol,
            timeframe,
            _bar_ts(b),
            _num(b.open),
            _num(b.high),
            _num(b.low),
            _num(b.close),
            _num(getattr(b, "volume", 0) or 0),
        ))

    if not rows:
        return 0

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO market_bars (
                    symbol, timeframe, ts, open, high, low, close, volume, source
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'finam_grpc_bars_v1')
                ON CONFLICT (symbol, timeframe, ts)
                DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    source = EXCLUDED.source
            """, rows)
        conn.commit()

    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--roots", default="BR,NG,USD")
    parser.add_argument("--symbols", default="")
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--max-contracts", type=int, default=3)
    parser.add_argument("--lookback-hours", type=int, default=72)
    parser.add_argument("--start-date", default="")
    parser.add_argument("--end-date", default="")
    args = parser.parse_args()

    roots = [x.strip() for x in args.roots.split(",") if x.strip()]

    migrate_market_bars()

    if args.symbols:
        symbols = [x.strip() for x in args.symbols.split(",") if x.strip()]
    else:
        symbols = load_contracts(roots, args.max_contracts)

    client = FinamBarsClient()

    if args.start_date and args.end_date:
        start = datetime.fromisoformat(args.start_date).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(args.end_date).replace(tzinfo=timezone.utc)
    else:
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=args.lookback_hours)

    total = 0

    try:
        for symbol in symbols:
            bars = []
            last_error = ""

            for attempt in range(1, 4):
                try:
                    resp = client.get_bars(
                        symbol=symbol,
                        timeframe=args.timeframe,
                        start=start,
                        end=end,
                    )
                    bars = list(getattr(resp, "bars", []) or [])
                    last_error = ""
                    break
                except grpc.RpcError as exc:
                    last_error = f"{exc.code()}:{exc.details()}"
                    print(
                        "FINAM_FUTURES_MARKET_BARS_RETRY "
                        f"symbol={symbol} timeframe={args.timeframe} "
                        f"attempt={attempt} error={last_error}",
                        flush=True,
                    )
                    time.sleep(1.5 * attempt)

            if last_error:
                print(
                    "FINAM_FUTURES_MARKET_BARS_FAILED "
                    f"symbol={symbol} timeframe={args.timeframe} "
                    f"error={last_error}",
                    flush=True,
                )
                continue

            saved = save_bars(symbol, args.timeframe, bars)
            total += saved

            print(
                "FINAM_FUTURES_MARKET_BARS_OK "
                f"symbol={symbol} timeframe={args.timeframe} "
                f"received={len(bars)} saved={saved}",
                flush=True,
            )
    finally:
        client.close()

    print(
        "FINAM_FUTURES_MARKET_BARS_SUMMARY "
        f"symbols={len(symbols)} saved={total}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
