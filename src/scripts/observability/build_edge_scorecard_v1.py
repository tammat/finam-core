#!/usr/bin/env python3

import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise SystemExit("DATABASE_URL_NOT_SET")

SQL = """
SELECT
    symbol,
    closed_trades,
    profit_factor_without_max_win,
    expectancy_without_max_win,
    median_pnl,
    status,
    calculated_at
FROM analytics_edge_validation_metrics_v1
ORDER BY
    CASE status
        WHEN 'EDGE_CONFIRMED_V1' THEN 1
        WHEN 'EDGE_WEAK' THEN 2
        WHEN 'INSUFFICIENT_SAMPLE' THEN 3
        ELSE 4
    END,
    symbol;
"""

with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
    rows = list(conn.execute(SQL))

confirmed = [r for r in rows if r["status"] == "EDGE_CONFIRMED_V1"]
weak = [r for r in rows if r["status"] == "EDGE_WEAK"]
insufficient = [r for r in rows if r["status"] == "INSUFFICIENT_SAMPLE"]
rejected = [r for r in rows if r["status"] == "EDGE_REJECTED"]

print("=== EDGE SCORECARD V1 ===")
print()

print("ПОДТВЕРЖДЁННЫЙ EDGE")
if confirmed:
    for r in confirmed:
        print(
            f"{r['symbol']:<14} "
            f"trades={r['closed_trades']:<5} "
            f"pf={r['profit_factor_without_max_win']:.4f} "
            f"exp={r['expectancy_without_max_win']:.4f} "
            f"median={r['median_pnl']:.4f}"
        )
else:
    print("нет")

print()
print("СЛАБЫЙ / НАБЛЮДАТЬ")
if weak:
    for r in weak:
        print(
            f"{r['symbol']:<14} "
            f"trades={r['closed_trades']:<5} "
            f"pf={r['profit_factor_without_max_win']:.4f} "
            f"exp={r['expectancy_without_max_win']:.4f}"
        )
else:
    print("нет")

print()
print("НЕДОСТАТОЧНО ДАННЫХ")
if insufficient:
    for r in insufficient:
        print(f"{r['symbol']:<14} trades={r['closed_trades']}")
else:
    print("нет")

print()
print("ОТКЛОНЕНЫ")
if rejected:
    for r in rejected:
        print(
            f"{r['symbol']:<14} "
            f"trades={r['closed_trades']:<5} "
            f"pf={r['profit_factor_without_max_win']:.4f} "
            f"exp={r['expectancy_without_max_win']:.4f} "
            f"median={r['median_pnl']:.4f}"
        )
else:
    print("нет")

print()
print("ИТОГО:")
print(f"ПОДТВЕРЖДЕНО={len(confirmed)}")
print(f"НАБЛЮДАТЬ={len(weak)}")
print(f"МАЛО_ДАННЫХ={len(insufficient)}")
print(f"ОТКЛОНЕНО={len(rejected)}")
