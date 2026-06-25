#!/usr/bin/env python3

import os
import psycopg2

SOURCE = "universe_backfill_v1"


def main() -> int:
    print("=== GLOBAL_MARKET_STATE_LINKING_V1 ===")
    print("mode=link_apply")
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

    linked = 0
    no_snapshot = 0
    entry_only = 0

    with psycopg2.connect(db) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id::text, symbol, timeframe, entry_ts, exit_ts
                FROM public.closed_trades
                WHERE symbol IS NOT NULL
                  AND timeframe IS NOT NULL
                  AND entry_ts IS NOT NULL
                  AND net_pnl IS NOT NULL
                ORDER BY entry_ts;
            """)
            trades = cur.fetchall()

            for trade_id, symbol, timeframe, entry_ts, exit_ts in trades:
                cur.execute("""
                    SELECT snapshot_id, compact_signature
                    FROM research.market_state_snapshots_v1
                    WHERE symbol=%s
                      AND timeframe=%s
                      AND source=%s
                      AND snapshot_ts<=%s
                    ORDER BY snapshot_ts DESC
                    LIMIT 1;
                """, (symbol, timeframe, SOURCE, entry_ts))
                entry = cur.fetchone()

                if not entry:
                    cur.execute("""
                        INSERT INTO research.trade_state_snapshots_v1 (
                            trade_id, symbol, timeframe, entry_ts, exit_ts,
                            link_quality, link_reason
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT(trade_id)
                        DO UPDATE SET
                            symbol=EXCLUDED.symbol,
                            timeframe=EXCLUDED.timeframe,
                            entry_ts=EXCLUDED.entry_ts,
                            exit_ts=EXCLUDED.exit_ts,
                            link_quality=EXCLUDED.link_quality,
                            link_reason=EXCLUDED.link_reason;
                    """, (
                        trade_id, symbol, timeframe, entry_ts, exit_ts,
                        "NO_SNAPSHOT",
                        "no_global_universe_market_state_snapshot_found",
                    ))
                    no_snapshot += 1
                    continue

                entry_snapshot_id, entry_signature = entry
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
                    """, (symbol, timeframe, SOURCE, exit_ts))
                    exit_row = cur.fetchone()
                    if exit_row:
                        exit_snapshot_id, exit_signature = exit_row

                quality = "EXACT_OR_NEAREST_OK"
                reason = "linked_closed_trades_to_global_universe_market_state"
                if exit_ts is not None and exit_snapshot_id is None:
                    quality = "ENTRY_ONLY"
                    reason = "entry_snapshot_found_exit_snapshot_missing"
                    entry_only += 1

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
                    trade_id, symbol, timeframe, entry_ts, exit_ts,
                    entry_snapshot_id, exit_snapshot_id,
                    entry_signature, exit_signature,
                    quality, reason,
                ))
                linked += 1

        conn.commit()

    print(f"linked_rows={linked}")
    print(f"no_snapshot={no_snapshot}")
    print(f"entry_only={entry_only}")
    print("db_update=1")
    print("VERDICT=GLOBAL_MARKET_STATE_LINKING_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
