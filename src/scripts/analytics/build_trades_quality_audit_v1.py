from __future__ import annotations

import subprocess
from typing import Any

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


def git_clean() -> bool:
    r = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, check=False)
    return r.stdout.strip() == ""


def print_rows(prefix: str, rows: list[dict[str, Any]]) -> None:
    for row in rows:
        print(" ".join([prefix] + [f"{k}={v}" for k, v in row.items()]), flush=True)


SUMMARY_SQL = """
SELECT
    count(*) AS total_trades,
    count(*) FILTER (WHERE payload ? 'signal_id') AS with_payload_signal_id,
    count(*) FILTER (WHERE payload ? 'strategy') AS with_payload_strategy,
    count(*) FILTER (WHERE payload = '{}'::jsonb OR payload IS NULL) AS empty_payload,
    count(*) FILTER (WHERE strategy <> '') AS with_strategy_column,
    count(*) FILTER (WHERE fill_id IS NOT NULL) AS with_fill_id,
    count(*) FILTER (WHERE is_invalid = true) AS invalid_rows
FROM trades;
"""

BY_SOURCE_SQL = """
SELECT
    trade_source,
    origin,
    strategy,
    timeframe,
    count(*) AS rows,
    count(*) FILTER (WHERE payload = '{}'::jsonb OR payload IS NULL) AS empty_payload,
    count(*) FILTER (WHERE payload ? 'signal_id') AS with_signal_id,
    count(*) FILTER (WHERE is_invalid) AS invalid_rows,
    min(created_at) AS first_ts,
    max(created_at) AS last_ts
FROM trades
GROUP BY trade_source, origin, strategy, timeframe
ORDER BY rows DESC
LIMIT 50;
"""

VALID_CANDIDATE_SQL = """
SELECT
    symbol,
    strategy,
    timeframe,
    origin,
    count(*) AS rows,
    count(*) FILTER (WHERE side = 'BUY') AS buy_rows,
    count(*) FILTER (WHERE side = 'SELL') AS sell_rows,
    min(created_at) AS first_ts,
    max(created_at) AS last_ts
FROM trades
WHERE is_invalid = false
  AND (
        payload ? 'signal_id'
        OR strategy <> ''
      )
  AND origin NOT IN ('backfill_from_fills')
GROUP BY symbol, strategy, timeframe, origin
ORDER BY rows DESC
LIMIT 50;
"""


def main() -> int:
    print("TRADES_QUALITY_AUDIT_V1", flush=True)
    print(f"TRADES_QUALITY_AUDIT_CONFIG git_clean={git_clean()}", flush=True)

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(SUMMARY_SQL)
            summary = [dict(cur.fetchone() or {})]

            cur.execute(BY_SOURCE_SQL)
            by_source = [dict(x) for x in cur.fetchall()]

            cur.execute(VALID_CANDIDATE_SQL)
            candidates = [dict(x) for x in cur.fetchall()]

    print_rows("TRADES_QUALITY_SUMMARY", summary)
    print_rows("TRADES_QUALITY_SOURCE", by_source)
    print_rows("TRADES_ANALYTICS_CANDIDATE", candidates)

    print("TRADES_QUALITY_AUDIT_VERDICT status=GROUND_TRUTH_IS_TRADES closed_trades_v1_status=RECONSTRUCTED_NOT_EDGE_SAFE", flush=True)
    print("TRADES_QUALITY_AUDIT_V1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
