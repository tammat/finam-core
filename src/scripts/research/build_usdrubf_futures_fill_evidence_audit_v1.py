from __future__ import annotations

import os

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql


SCHEMA = "analytics"
TABLE = "v_futures_fill_evidence_verified_v1"

SYMBOL_CANDIDATES = (
    "symbol",
    "instrument",
    "ticker",
    "security_code",
)

TS_CANDIDATES = (
    "execution_ts",
    "ts",
    "timestamp",
    "trade_ts",
    "fill_ts",
    "executed_at",
    "created_at",
)

QTY_CANDIDATES = (
    "quantity_contracts",
    "quantity",
    "qty",
    "filled_qty",
    "executed_qty",
)

PRICE_CANDIDATES = (
    "price",
    "fill_price",
    "executed_price",
)


def resolve_column(
    available: set[str],
    candidates: tuple[str, ...],
    role: str,
) -> str:
    matches = [
        name
        for name in candidates
        if name in available
    ]

    if len(matches) != 1:
        raise RuntimeError(
            "ERROR=FILL_COLUMN_CONTRACT_UNRESOLVED "
            f"role={role} "
            f"matches={matches}"
        )

    return matches[0]


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")

    if not dsn:
        raise SystemExit(
            "ERROR=DATABASE_URL_NOT_SET"
        )

    with psycopg2.connect(dsn) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema=%s
                  AND table_name=%s
                ORDER BY ordinal_position
                """,
                (SCHEMA, TABLE),
            )

            columns = [
                str(row["column_name"])
                for row in cur.fetchall()
            ]

            available = set(columns)

            print(
                "SOURCE_CONTRACT "
                f"schema={SCHEMA} "
                f"table={TABLE} "
                f"columns={','.join(columns)}"
            )

            symbol_col = resolve_column(
                available,
                SYMBOL_CANDIDATES,
                "symbol",
            )

            ts_col = resolve_column(
                available,
                TS_CANDIDATES,
                "timestamp",
            )

            qty_col = resolve_column(
                available,
                QTY_CANDIDATES,
                "quantity",
            )

            price_col = resolve_column(
                available,
                PRICE_CANDIDATES,
                "price",
            )

            print(
                "RESOLVED_COLUMNS "
                f"symbol={symbol_col} "
                f"timestamp={ts_col} "
                f"quantity={qty_col} "
                f"price={price_col}"
            )

            query = sql.SQL(
                """
                SELECT
                    {symbol}::text AS symbol,
                    COUNT(*) AS fill_rows,
                    SUM(abs({qty}))::numeric
                        AS executed_contracts,
                    MIN({ts}) AS first_ts,
                    MAX({ts}) AS last_ts
                FROM {schema}.{table}
                WHERE {symbol}::text IN (
                    'USDRUBF',
                    'USDRUBF@RTSX'
                )
                GROUP BY {symbol}
                ORDER BY {symbol}
                """
            ).format(
                symbol=sql.Identifier(symbol_col),
                qty=sql.Identifier(qty_col),
                ts=sql.Identifier(ts_col),
                schema=sql.Identifier(SCHEMA),
                table=sql.Identifier(TABLE),
            )

            cur.execute(query)

            rows = cur.fetchall()

            for row in rows:
                print(
                    "USDRUBF_FILL_ROW "
                    f"symbol={row['symbol']} "
                    f"fill_rows={row['fill_rows']} "
                    f"executed_contracts="
                    f"{row['executed_contracts']} "
                    f"first_ts={row['first_ts']} "
                    f"last_ts={row['last_ts']}"
                )

            # Проверяем отдельно именно даты,
            # по которым у нас имеется broker commission evidence.
            query_dates = sql.SQL(
                """
                SELECT
                    d.trade_date,
                    d.commission_total,
                    COUNT(f.*) AS usdrubf_fill_rows,
                    COALESCE(
                        SUM(abs(f.{qty})),
                        0
                    )::numeric AS executed_contracts
                FROM analytics.futures_commission_daily_v1 d
                LEFT JOIN {schema}.{table} f
                  ON f.{ts} >= d.trade_date
                 AND f.{ts} < d.trade_date + interval '1 day'
                 AND f.{symbol}::text IN (
                     'USDRUBF',
                     'USDRUBF@RTSX'
                 )
                WHERE d.evidence_status='VERIFIED'
                GROUP BY
                    d.trade_date,
                    d.commission_total
                ORDER BY d.trade_date
                """
            ).format(
                qty=sql.Identifier(qty_col),
                schema=sql.Identifier(SCHEMA),
                table=sql.Identifier(TABLE),
                ts=sql.Identifier(ts_col),
                symbol=sql.Identifier(symbol_col),
            )

            cur.execute(query_dates)

            overlap_rows = cur.fetchall()

            overlap_days = 0
            overlap_contracts = 0

            for row in overlap_rows:
                contracts = float(
                    row["executed_contracts"] or 0
                )

                if contracts > 0:
                    overlap_days += 1
                    overlap_contracts += contracts

                    print(
                        "USDRUBF_COMMISSION_OVERLAP_ROW "
                        f"trade_date={row['trade_date']} "
                        f"daily_commission="
                        f"{row['commission_total']} "
                        f"fill_rows="
                        f"{row['usdrubf_fill_rows']} "
                        f"executed_contracts="
                        f"{row['executed_contracts']}"
                    )

    if rows:
        evidence_status = (
            "USDRUBF_FILLS_EXIST_OUTSIDE_OR_INSIDE_"
            "COMMISSION_EVIDENCE_WINDOW"
        )
    else:
        evidence_status = (
            "USDRUBF_VERIFIED_FILLS_NOT_AVAILABLE"
        )

    print(
        f"usdrubf_verified_fill_symbols={len(rows)}"
    )

    print(
        f"commission_overlap_days={overlap_days}"
    )

    print(
        f"commission_overlap_contracts={overlap_contracts}"
    )

    print(
        f"evidence_status={evidence_status}"
    )

    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("economic_edge_claimed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "USDRUBF_FUTURES_FILL_EVIDENCE_AUDIT_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
