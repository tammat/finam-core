from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


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
            rows = [r[0] for r in cur.fetchall()]

    result: list[str] = []
    per_root: dict[str, int] = {}

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            for symbol in rows:
                cur.execute(
                    """
                    SELECT root_symbol
                    FROM futures_contract_universe
                    WHERE contract_symbol=%s
                    """,
                    (symbol,),
                )
                root = cur.fetchone()[0]
                per_root[root] = per_root.get(root, 0) + 1
                if per_root[root] <= max_contracts:
                    result.append(symbol)

    return result


def migrate_market_bars() -> None:
    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
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
                    source TEXT NOT NULL DEFAULT 'unknown',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, timeframe, ts)
                );

                ALTER TABLE market_bars
                ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'unknown';

                CREATE INDEX IF NOT EXISTS idx_market_bars_symbol_tf_ts
                ON market_bars(symbol, timeframe, ts DESC);
                """
            )
        conn.commit()


def generate_synthetic_backfill(
    *,
    symbol: str,
    timeframe: str,
    bars: int,
) -> int:
    """
    Русский комментарий:
    Временный безопасный backfill для проверки regime engine.
    Не имитирует реальный рынок, но позволяет проверить pipeline.
    source='synthetic_futures_backfill_v1' явно отделяет эти бары от реальных.
    """
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    if timeframe.upper() == "M5":
        step = timedelta(minutes=5)
    elif timeframe.upper() == "M1":
        step = timedelta(minutes=1)
    else:
        step = timedelta(minutes=5)

    base_price = {
        "BR": 80.0,
        "NG": 3.0,
        "USD": 90.0,
    }

    if symbol.startswith("BR"):
        base = base_price["BR"]
    elif symbol.startswith("NG"):
        base = base_price["NG"]
    elif symbol.startswith("USDRUB"):
        base = base_price["USD"]
    else:
        base = 100.0

    rows = []
    for i in range(bars):
        ts = now - step * (bars - i)
        drift = i * 0.0005
        wave = ((i % 12) - 6) * 0.001
        close = base * (1 + drift + wave)
        open_ = close * (1 - 0.0005)
        high = max(open_, close) * 1.001
        low = min(open_, close) * 0.999
        volume = 1

        rows.append((symbol, timeframe, ts, open_, high, low, close, volume))

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO market_bars (
                    symbol, timeframe, ts, open, high, low, close, volume, source
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'synthetic_futures_backfill_v1')
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
    parser.add_argument("--max-contracts", type=int, default=3)
    parser.add_argument("--bars", type=int, default=120)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()

    roots = [x.strip() for x in args.roots.split(",") if x.strip()]

    migrate_market_bars()

    symbols = load_contracts(roots, args.max_contracts)

    total = 0

    for symbol in symbols:
        if not args.synthetic:
            print(
                "FUTURES_MARKET_BARS_BACKFILL_SKIPPED "
                f"symbol={symbol} reason=real_provider_not_wired_use_--synthetic",
                flush=True,
            )
            continue

        inserted = generate_synthetic_backfill(
            symbol=symbol,
            timeframe=args.timeframe,
            bars=args.bars,
        )
        total += inserted

        print(
            "FUTURES_MARKET_BARS_BACKFILL_OK "
            f"symbol={symbol} timeframe={args.timeframe} bars={inserted}",
            flush=True,
        )

    print(
        "FUTURES_MARKET_BARS_BACKFILL_SUMMARY "
        f"symbols={len(symbols)} bars={total} synthetic={args.synthetic}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
