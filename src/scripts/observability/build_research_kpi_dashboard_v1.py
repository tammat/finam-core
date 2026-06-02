#!/usr/bin/env python3

import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("DATABASE_URL")
TARGET = 100

if not DATABASE_URL:
    raise SystemExit("DATABASE_URL_NOT_SET")

SQL = """
WITH fill_stats AS (
    SELECT
        symbol,
        COUNT(*) AS fills,
        FLOOR(COUNT(*) / 2.0)::int AS closed_trades
    FROM fills
    WHERE symbol IN (
        'PLZL@MISX',
        'LKOH@MISX',
        'SBER@MISX',
        'SBERP@MISX',
        'NVTK@MISX',
        'OZON@MISX',
        'GAZP@MISX',
        'BRM6@RTSX',
        'BRN6@RTSX',
        'SFIN@MISX',
        'T@MISX',
        'EUTR@MISX',
        'VTBR@MISX',
        'X5@MISX',
        'USDRUBF@RTSX',
        'NGN6@RTSX'
    )
    GROUP BY symbol
),
normalized AS (
    SELECT
        CASE
            WHEN symbol LIKE 'BR%@RTSX' THEN 'BRENT'
            WHEN symbol LIKE 'NG%@RTSX' THEN 'NG'
            WHEN symbol = 'USDRUBF@RTSX' THEN 'USDRUB'
            ELSE replace(replace(symbol, '@MISX', ''), '@RTSX', '')
        END AS instrument,
        SUM(closed_trades)::int AS trades
    FROM fill_stats
    GROUP BY 1
)
SELECT instrument, trades
FROM normalized
ORDER BY trades DESC, instrument;
"""

with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
    rows = list(conn.execute(SQL))

ready = [r for r in rows if int(r["trades"]) >= TARGET]
progress = [r for r in rows if int(r["trades"]) < TARGET]

print("=== KPI ИССЛЕДОВАТЕЛЬСКОГО КОНТУРА ===")
print()
print("ИНСТРУМЕНТ     СДЕЛКИ   ГОТОВНОСТЬ")
print()

for row in ready:
    print(f"{row['instrument']:<12} {int(row['trades']):>6}    ГОТОВ")

print()

for row in progress:
    trades = int(row["trades"])
    pct = min(100, round((trades / TARGET) * 100))
    print(f"{row['instrument']:<12} {trades:>6}    {pct}%")

print()
print("ИТОГО:")
print(f"ГОТОВЫ={len(ready)}")
print(f"В РАБОТЕ={len(progress)}")
