from __future__ import annotations

import psycopg2
import psycopg2.extras


DB = "postgresql:///finam_core"


def rows(cur, sql, params=None):
    if params is None:
        cur.execute(sql)
    else:
        cur.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


def main() -> int:
    with psycopg2.connect(DB) as conn:
        conn.set_session(readonly=True, autocommit=False)

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            runtime = rows(
                cur,
                """
                SELECT
                    symbol,
                    strategy,
                    regime,
                    priority,
                    is_enabled,
                    source,
                    allocated_at,
                    last_seen_at,
                    disabled_at,
                    disable_reason,
                    updated_at,
                    raw_json
                FROM runtime_active_universe
                WHERE symbol LIKE 'BR%@RTSX'
                ORDER BY symbol
                """
            )

            print("=== BRENT RUNTIME ===")
            for row in runtime:
                print(
                    "BRENT_RUNTIME_ROW "
                    f"symbol={row['symbol']} "
                    f"enabled={int(bool(row['is_enabled']))} "
                    f"source={row['source']} "
                    f"updated_at={row['updated_at']}"
                )

            specs = rows(
                cur,
                """
                WITH latest AS (
                    SELECT DISTINCT ON (symbol)
                        symbol,
                        source_payload,
                        created_at
                    FROM analytics.contract_spec_sync_item_v1
                    WHERE symbol LIKE 'BR%@RTSX'
                      AND status_code IN (
                          'CREATED',
                          'UPDATED',
                          'UNCHANGED'
                      )
                      AND source_payload ? 'LASTTRADEDATE'
                    ORDER BY symbol,created_at DESC
                )
                SELECT
                    symbol,
                    source_payload->>'LASTTRADEDATE'
                        AS last_trade_date,
                    created_at
                FROM latest
                ORDER BY
                    (source_payload->>'LASTTRADEDATE')::date,
                    symbol
                """
            )

            print("=== BRENT CONTRACTS ===")
            for row in specs:
                print(
                    "BRENT_CONTRACT_ROW "
                    f"symbol={row['symbol']} "
                    f"last_trade_date={row['last_trade_date']} "
                    f"spec_at={row['created_at']}"
                )

            for table in (
                "futures_roll_decision_v1",
                "v5_futures_rollover_decision_v1",
                "v5_futures_rollover_state_v1",
            ):
                cur.execute(
                    """
                    SELECT EXISTS(
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema='analytics'
                          AND table_name=%s
                    )
                    """,
                    (table,),
                )
                exists = bool(cur.fetchone()["exists"])

                print(
                    f"roll_table={table} "
                    f"exists={int(exists)}"
                )

                if exists:
                    cur.execute(
                        f"""
                        SELECT *
                        FROM analytics.{table}
                        ORDER BY 1 DESC
                        LIMIT 20
                        """
                    )

                    data = [
                        dict(r)
                        for r in cur.fetchall()
                    ]

                    for row in data:
                        if "BR" in repr(row):
                            print(
                                f"ROLL_ROW table={table} "
                                f"data={row!r}"
                            )

    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "BRENT_RUNTIME_ROLL_RESOLUTION_AUDIT_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
