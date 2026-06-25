#!/usr/bin/env python3

import os
import psycopg2


def main():

    print("=== MARKET_INDEX_CONTEXT_LINKING_V1 ===")
    print("mode=link_apply")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("orders_sent=0")

    db = os.environ.get("DATABASE_URL","")

    if not db:
        print("db_update=0")
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2

    if db.startswith("sqlite"):
        print("db_update=0")
        print("ERROR=SQLITE_FORBIDDEN")
        return 2

    linked = 0

    with psycopg2.connect(db) as conn:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT
                    trade_state_id,
                    trade_id,
                    entry_snapshot_id,
                    entry_compact_signature,
                    entry_ts
                FROM research.trade_state_snapshots_v1
                WHERE link_quality='EXACT_OR_NEAREST_OK'
                ORDER BY entry_ts;
            """)

            trades = cur.fetchall()

            for (
                trade_state_id,
                trade_id,
                entry_snapshot_id,
                entry_signature,
                entry_ts,
            ) in trades:

                for context_code in ("FX_USDRUB", "ENERGY_BR"):

                    cur.execute("""
                        SELECT
                            context_id,
                            compact_context_signature
                        FROM research.market_index_state_context_v1
                        WHERE context_code=%s
                          AND context_ts<=%s
                        ORDER BY context_ts DESC
                        LIMIT 1;
                    """, (context_code, entry_ts))

                    row = cur.fetchone()

                    if row is None:
                        continue

                    context_id, context_signature = row

                    cur.execute("""
                        INSERT INTO
                        research.market_state_index_context_links_v1
                        (
                            trade_state_id,
                            trade_id,
                            entry_snapshot_id,
                            entry_compact_signature,
                            context_id,
                            context_code,
                            context_compact_signature,
                            link_quality,
                            link_reason
                        )
                        VALUES
                        (
                            %s,%s,%s,%s,
                            %s,%s,%s,
                            %s,%s
                        )

                        ON CONFLICT
                        (
                            trade_state_id,
                            context_code
                        )

                        DO UPDATE SET

                            context_id=EXCLUDED.context_id,
                            context_compact_signature=EXCLUDED.context_compact_signature,
                            link_quality=EXCLUDED.link_quality,
                            link_reason=EXCLUDED.link_reason;
                    """,
                    (
                        trade_state_id,
                        trade_id,
                        entry_snapshot_id,
                        entry_signature,
                        context_id,
                        context_code,
                        context_signature,
                        "EXACT_OR_NEAREST_OK",
                        "nearest_prior_index_context",
                    ))

                    linked += 1

        conn.commit()

    print(f"context_links={linked}")
    print("db_update=1")
    print("VERDICT=MARKET_INDEX_CONTEXT_LINKING_OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
