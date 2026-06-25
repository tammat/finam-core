#!/usr/bin/env python3

import os
import psycopg2

SOURCE = "universe_backfill_v1"


def map_timeframe(symbol: str, timeframe: str) -> str:
    if symbol in ("NGN6@RTSX", "BRN6@RTSX") and timeframe in ("LIVE", "M1"):
        return "M5"
    return timeframe


def main() -> int:
    print("=== GLOBAL_LINK_REPAIR_IMPLEMENTATION_V1 ===")
    print("mode=repair_apply")
    print("repair_type=TIMEFRAME_MISMATCH_MAP_LIVE_M1_TO_M5")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("orders_sent=0")

    db = os.environ.get("DATABASE_URL", "")
    if not db:
        print("db_update=0")
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2
    if db.startswith("sqlite"):
        print("db_update=0")
        print("ERROR=SQLITE_FORBIDDEN")
        return 2

    repaired = 0
    still_missing = 0

    with psycopg2.connect(db) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    ct.id::text,
                    ct.symbol,
                    ct.timeframe,
                    ct.entry_ts,
                    ct.exit_ts
                FROM public.closed_trades ct
                LEFT JOIN research.trade_state_snapshots_v1 tss
                  ON tss.trade_id = ct.id::text
                WHERE ct.symbol IN ('NGN6@RTSX','BRN6@RTSX')
                  AND ct.timeframe IN ('LIVE','M1')
                  AND ct.entry_ts IS NOT NULL
                  AND ct.net_pnl IS NOT NULL
                  AND COALESCE(tss.link_quality, 'NO_LINK_ROW') <> 'EXACT_OR_NEAREST_OK'
                ORDER BY ct.symbol, ct.entry_ts;
            """)
            trades = cur.fetchall()

            for trade_id, symbol, original_tf, entry_ts, exit_ts in trades:
                mapped_tf = map_timeframe(symbol, original_tf)

                cur.execute("""
                    SELECT snapshot_id, compact_signature
                    FROM research.market_state_snapshots_v1
                    WHERE symbol=%s
                      AND timeframe=%s
                      AND source=%s
                      AND snapshot_ts<=%s
                    ORDER BY snapshot_ts DESC
                    LIMIT 1;
                """, (symbol, mapped_tf, SOURCE, entry_ts))
                entry_row = cur.fetchone()

                if not entry_row:
                    still_missing += 1
                    continue

                entry_snapshot_id, entry_signature = entry_row
                exit_snapshot_id = None
                exit_signature = None

                if exit_ts is not None:
                    cur.execute("""
                        SELECT snapshot_id, compact_signature
                        FROM research.market_state_snapshots_v1
                        WHERE symbol=%s
                          AND timeframe=%s
                          AND source=%s
                          AND snapshot_ts<=%s
                        ORDER BY snapshot_ts DESC
                        LIMIT 1;
                    """, (symbol, mapped_tf, SOURCE, exit_ts))
                    exit_row = cur.fetchone()
                    if exit_row:
                        exit_snapshot_id, exit_signature = exit_row

                quality = "EXACT_OR_NEAREST_OK"
                reason = (
                    "global_link_repair_v1_timeframe_mapped_"
                    f"{original_tf}_to_{mapped_tf}"
                )

                if exit_ts is not None and exit_snapshot_id is None:
                    quality = "ENTRY_ONLY"
                    reason = (
                        "global_link_repair_v1_entry_only_timeframe_mapped_"
                        f"{original_tf}_to_{mapped_tf}"
                    )

                cur.execute("""
                    INSERT INTO research.trade_state_snapshots_v1 (
                        trade_id,
                        symbol,
                        timeframe,
                        entry_ts,
                        exit_ts,
                        entry_snapshot_id,
                        exit_snapshot_id,
                        entry_compact_signature,
                        exit_compact_signature,
                        holding_snapshot_count,
                        link_quality,
                        link_reason
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,0,%s,%s)
                    ON CONFLICT(trade_id)
                    DO UPDATE SET
                        symbol=EXCLUDED.symbol,
                        timeframe=EXCLUDED.timeframe,
                        entry_ts=EXCLUDED.entry_ts,
                        exit_ts=EXCLUDED.exit_ts,
                        entry_snapshot_id=EXCLUDED.entry_snapshot_id,
                        exit_snapshot_id=EXCLUDED.exit_snapshot_id,
                        entry_compact_signature=EXCLUDED.entry_compact_signature,
                        exit_compact_signature=EXCLUDED.exit_compact_signature,
                        holding_snapshot_count=EXCLUDED.holding_snapshot_count,
                        link_quality=EXCLUDED.link_quality,
                        link_reason=EXCLUDED.link_reason;
                """, (
                    trade_id,
                    symbol,
                    original_tf,
                    entry_ts,
                    exit_ts,
                    entry_snapshot_id,
                    exit_snapshot_id,
                    entry_signature,
                    exit_signature,
                    quality,
                    reason,
                ))

                repaired += 1

        conn.commit()

    print(f"repaired_rows={repaired}")
    print(f"still_missing={still_missing}")
    print("mapped_timeframes=LIVE->M5,M1->M5")
    print("target_symbols=NGN6@RTSX,BRN6@RTSX")
    print("db_update=1")
    print("VERDICT=GLOBAL_LINK_REPAIR_IMPLEMENTATION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
