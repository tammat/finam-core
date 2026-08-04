from __future__ import annotations

import argparse
import os

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "FEATURE_STORE_HISTORICAL_CORRECTION_FORENSIC_V1"

DEFAULT_WINDOW_BARS = int(
    os.getenv("FEATURE_STORE_CORRECTION_WINDOW_BARS", "20")
)
MAX_WINDOW_BARS = int(
    os.getenv("FEATURE_STORE_CORRECTION_MAX_WINDOW_BARS", "5000")
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only детализация расхождений OHLCV между "
            "public.market_bars и marketcore.market_snapshot_v1."
        )
    )
    parser.add_argument(
        "--window-bars",
        type=int,
        default=DEFAULT_WINDOW_BARS,
    )
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--timeframe", default=None)
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.window_bars < 1 or args.window_bars > MAX_WINDOW_BARS:
        raise SystemExit(
            f"ERROR=invalid_window_bars:{args.window_bars}"
        )

    if args.limit < 1 or args.limit > 10000:
        raise SystemExit(
            f"ERROR=invalid_limit:{args.limit}"
        )

    with psycopg2.connect(DB) as conn:
        conn.set_session(readonly=True, autocommit=False)

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(
                """
                WITH target_pairs AS (
                    SELECT
                        w.symbol,
                        w.timeframe
                    FROM analytics.feature_store_watermark_v1 w
                    WHERE (%s::text IS NULL OR w.symbol = %s)
                      AND (%s::text IS NULL OR w.timeframe = %s)
                ),
                recent_source AS (
                    SELECT
                        target.symbol,
                        target.timeframe,
                        source_bar.ts,
                        source_bar.open,
                        source_bar.high,
                        source_bar.low,
                        source_bar.close,
                        source_bar.volume
                    FROM target_pairs target
                    CROSS JOIN LATERAL (
                        SELECT
                            mb.ts,
                            mb.open,
                            mb.high,
                            mb.low,
                            mb.close,
                            mb.volume
                        FROM public.market_bars mb
                        WHERE mb.symbol = target.symbol
                          AND mb.timeframe = target.timeframe
                          AND mb.ts IS NOT NULL
                          AND mb.close IS NOT NULL
                        ORDER BY mb.ts DESC
                        LIMIT %s
                    ) source_bar
                ),
                differences AS (
                    SELECT
                        source.symbol,
                        source.timeframe,
                        source.ts,
                        snapshot.bar_ts IS NULL
                            AS snapshot_missing,

                        source.open AS source_open,
                        snapshot.open AS snapshot_open,
                        source.open IS DISTINCT FROM snapshot.open
                            AS open_changed,

                        source.high AS source_high,
                        snapshot.high AS snapshot_high,
                        source.high IS DISTINCT FROM snapshot.high
                            AS high_changed,

                        source.low AS source_low,
                        snapshot.low AS snapshot_low,
                        source.low IS DISTINCT FROM snapshot.low
                            AS low_changed,

                        source.close AS source_close,
                        snapshot.close AS snapshot_close,
                        source.close IS DISTINCT FROM snapshot.close
                            AS close_changed,

                        source.volume AS source_volume,
                        snapshot.volume AS snapshot_volume,
                        source.volume IS DISTINCT FROM snapshot.volume
                            AS volume_changed,

                        snapshot.source_version
                            AS snapshot_source_version,
                        snapshot.build_id
                            AS snapshot_build_id,
                        snapshot.refreshed_at
                            AS snapshot_refreshed_at
                    FROM recent_source source
                    LEFT JOIN marketcore.market_snapshot_v1 snapshot
                      ON snapshot.symbol = source.symbol
                     AND snapshot.timeframe = source.timeframe
                     AND snapshot.bar_ts = source.ts
                )
                SELECT *
                FROM differences
                WHERE snapshot_missing
                   OR open_changed
                   OR high_changed
                   OR low_changed
                   OR close_changed
                   OR volume_changed
                ORDER BY symbol, timeframe, ts DESC
                LIMIT %s
                """,
                (
                    args.symbol,
                    args.symbol,
                    args.timeframe,
                    args.timeframe,
                    args.window_bars,
                    VOLUME_TOLERANCE,
                    args.limit,
                ),
            )

            rows = [dict(row) for row in cur.fetchall()]

    pair_keys = {
        (row["symbol"], row["timeframe"])
        for row in rows
    }

    field_counts = {
        "open": sum(bool(row["open_changed"]) for row in rows),
        "high": sum(bool(row["high_changed"]) for row in rows),
        "low": sum(bool(row["low_changed"]) for row in rows),
        "close": sum(bool(row["close_changed"]) for row in rows),
        "volume": sum(bool(row["volume_changed"]) for row in rows),
        "missing": sum(bool(row["snapshot_missing"]) for row in rows),
    }

    print(
        "=== FEATURE_STORE_HISTORICAL_CORRECTION_FORENSIC_V1 ==="
    )
    print(f"source_version={SOURCE_VERSION}")
    print(f"window_bars={args.window_bars}")
    print(f"difference_rows={len(rows)}")
    print(f"difference_pairs={len(pair_keys)}")
    print(f"open_changed_rows={field_counts['open']}")
    print(f"high_changed_rows={field_counts['high']}")
    print(f"low_changed_rows={field_counts['low']}")
    print(f"close_changed_rows={field_counts['close']}")
    print(f"volume_changed_rows={field_counts['volume']}")
    print(f"snapshot_missing_rows={field_counts['missing']}")

    for symbol, timeframe in sorted(pair_keys):
        pair_rows = [
            row
            for row in rows
            if row["symbol"] == symbol
            and row["timeframe"] == timeframe
        ]
        print(
            "PAIR"
            f" symbol={symbol}"
            f" timeframe={timeframe}"
            f" changed_rows={len(pair_rows)}"
        )

    for row in rows:
        changed_fields = [
            field
            for field in ("open", "high", "low", "close", "volume")
            if row[f"{field}_changed"]
        ]

        print(
            "DIFF"
            f" symbol={row['symbol']}"
            f" timeframe={row['timeframe']}"
            f" ts={row['ts'].isoformat()}"
            f" fields={','.join(changed_fields) or 'snapshot_missing'}"
            f" source_open={row['source_open']}"
            f" snapshot_open={row['snapshot_open']}"
            f" source_high={row['source_high']}"
            f" snapshot_high={row['snapshot_high']}"
            f" source_low={row['source_low']}"
            f" snapshot_low={row['snapshot_low']}"
            f" source_close={row['source_close']}"
            f" snapshot_close={row['snapshot_close']}"
            f" source_volume={row['source_volume']}"
            f" snapshot_volume={row['snapshot_volume']}"
            f" snapshot_source_version="
            f"{row['snapshot_source_version']}"
            f" snapshot_refreshed_at="
            f"{row['snapshot_refreshed_at']}"
        )

    print("writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "FEATURE_STORE_HISTORICAL_CORRECTION_FORENSIC_V1_READY"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
