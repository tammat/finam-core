#!/usr/bin/env python3

import os
import psycopg2


CONTEXT_CODES = ("FX_USDRUB", "ENERGY_BR")


def main() -> int:
    print("=== GLOBAL_CONTEXT_LINKING_V1 ===")
    print("mode=context_link_apply")
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
    missing = 0

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
            trade_states = cur.fetchall()

            for trade_state_id, trade_id, entry_snapshot_id, entry_sig, entry_ts in trade_states:
                for context_code in CONTEXT_CODES:
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

                    if not row:
                        missing += 1
                        continue

                    context_id, context_sig = row

                    cur.execute("""
                        INSERT INTO research.market_state_index_context_links_v1 (
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
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (trade_state_id, context_code)
                        DO UPDATE SET
                            trade_id=EXCLUDED.trade_id,
                            entry_snapshot_id=EXCLUDED.entry_snapshot_id,
                            entry_compact_signature=EXCLUDED.entry_compact_signature,
                            context_id=EXCLUDED.context_id,
                            context_compact_signature=EXCLUDED.context_compact_signature,
                            link_quality=EXCLUDED.link_quality,
                            link_reason=EXCLUDED.link_reason;
                    """, (
                        trade_state_id,
                        trade_id,
                        entry_snapshot_id,
                        entry_sig,
                        context_id,
                        context_code,
                        context_sig,
                        "EXACT_OR_NEAREST_OK",
                        "global_context_linking_v1_nearest_prior_context",
                    ))

                    linked += 1

        conn.commit()

    print(f"context_links={linked}")
    print(f"context_missing={missing}")
    print(f"context_codes={','.join(CONTEXT_CODES)}")
    print("db_update=1")
    print("VERDICT=GLOBAL_CONTEXT_LINKING_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
