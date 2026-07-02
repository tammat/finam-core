from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

VIEWS = [
    "public.v_trades_equity_curve_ui",
    "public.v_trades_drawdown_curve_ui",
    "public.v_trades_pnl_auto_ui",
]

def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            print("=== PAPER_RUNTIME_EQUITY_CURVE_SOURCE_DISCOVERY_V1 ===")

            for view in VIEWS:
                schema, name = view.split(".")
                print(f"\nVIEW={view}")

                cur.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema=%s AND table_name=%s
                    ORDER BY ordinal_position;
                """, (schema, name))
                cols = cur.fetchall()

                print("COLUMNS")
                for col, typ in cols:
                    print(f"- {col}: {typ}")

                cur.execute(f"SELECT count(*) FROM {view};")
                print(f"ROWS={cur.fetchone()[0]}")

                cur.execute(f"SELECT * FROM {view} LIMIT 5;")
                rows = cur.fetchall()
                print("SAMPLE_ROWS")
                for row in rows:
                    print(row)

            print("\nVERDICT=PAPER_RUNTIME_EQUITY_CURVE_SOURCE_DISCOVERY_V1_READY")

if __name__ == "__main__":
    main()
