from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SQL = """
SELECT
    (ts AT TIME ZONE 'Europe/Moscow')::date AS trade_date,
    symbol,
    strategy,
    timeframe,
    block_type,
    block_reason,
    count(*) AS blocks,
    round(avg(price)::numeric, 4) AS avg_price,
    round(avg(atr)::numeric, 6) AS avg_atr,
    round(avg(atr_pct)::numeric, 6) AS avg_atr_pct,
    round(avg(threshold)::numeric, 6) AS avg_threshold,
    round(avg(compression_ratio)::numeric, 6) AS avg_compression_ratio,
    min(ts) AS first_ts,
    max(ts) AS last_ts
FROM runtime_guard_pre_signal_block_audit_v1
GROUP BY
    (ts AT TIME ZONE 'Europe/Moscow')::date,
    symbol,
    strategy,
    timeframe,
    block_type,
    block_reason
ORDER BY
    trade_date DESC,
    blocks DESC,
    symbol,
    block_type
"""


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(SQL)
            rows = [dict(r) for r in cur.fetchall()]

    print("PRE_SIGNAL_BLOCK_DAILY_SUMMARY_V1", flush=True)

    for r in rows:
        print(
            "PRE_SIGNAL_BLOCK_DAILY_ROW",
            f"date={r['trade_date']}",
            f"symbol={r['symbol']}",
            f"strategy={r['strategy']}",
            f"timeframe={r['timeframe']}",
            f"block_type={r['block_type']}",
            f"reason={r['block_reason']}",
            f"blocks={r['blocks']}",
            f"avg_atr_pct={r['avg_atr_pct']}",
            f"avg_threshold={r['avg_threshold']}",
            f"avg_compression_ratio={r['avg_compression_ratio']}",
            f"last_ts={r['last_ts']}",
            flush=True,
        )

    print(
        f"PRE_SIGNAL_BLOCK_DAILY_SUMMARY_V1_OK rows={len(rows)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
