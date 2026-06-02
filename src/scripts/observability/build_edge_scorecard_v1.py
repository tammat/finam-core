#!/usr/bin/env python3

import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise SystemExit("DATABASE_URL_NOT_SET")

SQL = """
SELECT
    e.symbol,
    e.closed_trades,
    e.profit_factor_without_max_win,
    e.expectancy_without_max_win,
    e.median_pnl,
    e.status AS edge_status,
    COALESCE(b.bias_status, 'EDGE_BIAS_NOT_CHECKED') AS bias_status,
    COALESCE(b.bias_reason, '') AS bias_reason,
    e.calculated_at
FROM analytics_edge_validation_metrics_v1 e
LEFT JOIN analytics_edge_bias_audit_v1 b
    ON b.symbol = e.symbol
ORDER BY e.symbol;
"""

with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
    rows = list(conn.execute(SQL))

confirmed = []
suspicious = []
weak = []
insufficient = []
rejected = []

for r in rows:
    edge_status = r["edge_status"]
    bias_status = r["bias_status"]

    final_status = edge_status

    # Русский комментарий: confirmed edge понижается, если bias-аудит выявил концентрацию.
    if edge_status == "EDGE_CONFIRMED_V1" and bias_status == "EDGE_SUSPICIOUS":
        final_status = "EDGE_SUSPICIOUS"

    if final_status == "EDGE_CONFIRMED_V1":
        confirmed.append(r)
    elif final_status == "EDGE_SUSPICIOUS":
        suspicious.append(r)
    elif final_status == "EDGE_WEAK":
        weak.append(r)
    elif final_status == "INSUFFICIENT_SAMPLE":
        insufficient.append(r)
    else:
        rejected.append(r)

def print_metric_row(r, include_bias=False):
    line = (
        f"{r['symbol']:<14} "
        f"trades={r['closed_trades']:<5} "
        f"pf={r['profit_factor_without_max_win']:.4f} "
        f"exp={r['expectancy_without_max_win']:.4f} "
        f"median={r['median_pnl']:.4f}"
    )
    print(line)

    if include_bias:
        print(f"  bias={r['bias_status']} reason={r['bias_reason']}")

print("=== EDGE SCORECARD V1 ===")
print()

print("ПОДТВЕРЖДЁННЫЙ EDGE")
if confirmed:
    for r in confirmed:
        print_metric_row(r)
else:
    print("нет")

print()
print("ПОДОЗРИТЕЛЬНЫЙ EDGE / ТРЕБУЕТ ПОВТОРНОГО НАКОПЛЕНИЯ")
if suspicious:
    for r in suspicious:
        print_metric_row(r, include_bias=True)
else:
    print("нет")

print()
print("СЛАБЫЙ / НАБЛЮДАТЬ")
if weak:
    for r in weak:
        print_metric_row(r)
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
        print_metric_row(r)
else:
    print("нет")

print()
print("ИТОГО:")
print(f"ПОДТВЕРЖДЕНО={len(confirmed)}")
print(f"ПОДОЗРИТЕЛЬНО={len(suspicious)}")
print(f"НАБЛЮДАТЬ={len(weak)}")
print(f"МАЛО_ДАННЫХ={len(insufficient)}")
print(f"ОТКЛОНЕНО={len(rejected)}")
