from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

TABLES = [
    "public.signals",
    "public.signal_lifecycle",
    "public.signal_fills",
    "public.fills",
    "public.closed_trades",
    "public.trade_context_snapshots",
    "public.trade_context_envelopes",
    "public.trade_risk_context",
    "public.signal_quality_audit_v1",
    "public.runtime_governance_live_accumulation_v1",
]


def print_columns(cur, table: str) -> None:
    schema, name = table.split(".")
    cur.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema=%s AND table_name=%s
        ORDER BY ordinal_position;
        """,
        (schema, name),
    )
    rows = cur.fetchall()
    print("COLUMNS")
    for col, typ in rows:
        print(f"- {col}: {typ}")


def print_sample(cur, table: str) -> None:
    try:
        cur.execute(f"SELECT * FROM {table} LIMIT 3;")
        rows = cur.fetchall()
        print("SAMPLE_ROWS")
        for row in rows:
            print(row)
    except Exception as exc:
        print(f"SAMPLE_ERROR={type(exc).__name__}:{exc}")


def print_candidate_links(cur) -> None:
    print("\n=== CANDIDATE_LINK_COLUMNS ===")
    cur.execute(
        """
        SELECT table_schema, table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema='public'
          AND (
              column_name ILIKE '%signal%'
              OR column_name ILIKE '%fill%'
              OR column_name ILIKE '%trade%'
              OR column_name ILIKE '%order%'
              OR column_name ILIKE '%intent%'
              OR column_name ILIKE '%context%'
              OR column_name ILIKE '%payload%'
          )
          AND table_name IN (
              'signals',
              'signal_lifecycle',
              'signal_fills',
              'fills',
              'closed_trades',
              'trade_context_snapshots',
              'trade_context_envelopes',
              'trade_risk_context',
              'signal_quality_audit_v1',
              'runtime_governance_live_accumulation_v1'
          )
        ORDER BY table_name, ordinal_position;
        """
    )
    for schema, table, col, typ in cur.fetchall():
        print(f"{schema}.{table}.{col}: {typ}")


def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            print("=== PAPER_RUNTIME_KNOWLEDGE_GRAPH_SOURCE_DISCOVERY_V1 ===")

            for table in TABLES:
                print(f"\nTABLE={table}")
                cur.execute("SELECT to_regclass(%s);", (table,))
                exists = cur.fetchone()[0] is not None
                print(f"EXISTS={exists}")
                if not exists:
                    continue

                cur.execute(f"SELECT count(*) FROM {table};")
                print(f"ROWS={cur.fetchone()[0]}")

                print_columns(cur, table)
                print_sample(cur, table)

            print_candidate_links(cur)

            print("\nVERDICT=PAPER_RUNTIME_KNOWLEDGE_GRAPH_SOURCE_DISCOVERY_V1_READY")


if __name__ == "__main__":
    main()
