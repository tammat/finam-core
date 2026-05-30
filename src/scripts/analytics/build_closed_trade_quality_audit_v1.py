from __future__ import annotations

import argparse
import subprocess
from typing import Any

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def print_rows(prefix: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        print(f"{prefix} empty=true", flush=True)
        return
    for row in rows:
        print(" ".join([prefix] + [f"{k}={v}" for k, v in row.items()]), flush=True)


SUMMARY_SQL = """
WITH q AS (
    SELECT
        *,
        CASE
            WHEN entry_price > 0 AND exit_price > 0
            THEN abs(exit_price / entry_price - 1)
            ELSE NULL
        END AS move_ratio,
        CASE
            WHEN signal_id IS NULL THEN 'SIGNAL_ID_NULL'
            WHEN payload IS NULL OR payload = '{}'::jsonb THEN 'EMPTY_PAYLOAD'
            WHEN entry_price <= 0 OR exit_price <= 0 THEN 'BAD_PRICE'
            WHEN entry_price > 0 AND exit_price > 0
                 AND abs(exit_price / entry_price - 1) > %(outlier_pct)s
                THEN 'OUTLIER_MOVE'
            ELSE 'VALID'
        END AS quality_status
    FROM closed_trades
    WHERE coalesce(closed_at, exit_ts, created_at) >= now() - (%(window_days)s * interval '1 day')
)
SELECT
    source,
    trade_source,
    quality_status,
    count(*) AS rows,
    count(*) FILTER (WHERE symbol LIKE 'BR%%') AS br_rows,
    count(*) FILTER (WHERE symbol LIKE 'NG%%') AS ng_rows,
    count(*) FILTER (WHERE symbol = 'USDRUBF@RTSX') AS usd_rows,
    round(sum(net_pnl)::numeric, 6) AS net_pnl,
    min(created_at) AS first_created,
    max(created_at) AS last_created
FROM q
GROUP BY source, trade_source, quality_status
ORDER BY rows DESC, source, trade_source, quality_status;
"""


SUSPECT_BATCH_SQL = """
SELECT
    created_at,
    source,
    trade_source,
    count(*) AS rows,
    count(*) FILTER (WHERE signal_id IS NULL) AS signal_null_rows,
    count(*) FILTER (WHERE payload IS NULL OR payload = '{}'::jsonb) AS empty_payload_rows,
    round(sum(net_pnl)::numeric, 6) AS net_pnl,
    min(opened_at) AS first_opened,
    max(closed_at) AS last_closed
FROM closed_trades
GROUP BY created_at, source, trade_source
HAVING count(*) >= %(min_batch_rows)s
ORDER BY rows DESC, created_at DESC
LIMIT %(limit_rows)s;
"""


SYMBOL_SQL = """
WITH q AS (
    SELECT
        symbol,
        net_pnl,
        CASE
            WHEN signal_id IS NULL THEN 'SIGNAL_ID_NULL'
            WHEN payload IS NULL OR payload = '{}'::jsonb THEN 'EMPTY_PAYLOAD'
            WHEN entry_price <= 0 OR exit_price <= 0 THEN 'BAD_PRICE'
            WHEN entry_price > 0 AND exit_price > 0
                 AND abs(exit_price / entry_price - 1) > %(outlier_pct)s
                THEN 'OUTLIER_MOVE'
            ELSE 'VALID'
        END AS quality_status
    FROM closed_trades
    WHERE coalesce(closed_at, exit_ts, created_at) >= now() - (%(window_days)s * interval '1 day')
)
SELECT
    symbol,
    quality_status,
    count(*) AS rows,
    round(sum(net_pnl)::numeric, 6) AS net_pnl
FROM q
GROUP BY symbol, quality_status
ORDER BY symbol, quality_status;
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-days", type=int, default=365)
    parser.add_argument("--outlier-pct", type=float, default=0.20)
    parser.add_argument("--min-batch-rows", type=int, default=20)
    parser.add_argument("--limit-rows", type=int, default=50)
    args = parser.parse_args()

    params = {
        "window_days": args.window_days,
        "outlier_pct": args.outlier_pct,
        "min_batch_rows": args.min_batch_rows,
        "limit_rows": args.limit_rows,
    }

    print("CLOSED_TRADE_QUALITY_AUDIT_V1", flush=True)
    print(
        "CLOSED_TRADE_QUALITY_CONFIG "
        f"window_days={args.window_days} "
        f"outlier_pct={args.outlier_pct} "
        f"min_batch_rows={args.min_batch_rows} "
        f"git_clean={git_clean()}",
        flush=True,
    )

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(SUMMARY_SQL, params)
            summary = [dict(x) for x in cur.fetchall()]

            cur.execute(SUSPECT_BATCH_SQL, params)
            batches = [dict(x) for x in cur.fetchall()]

            cur.execute(SYMBOL_SQL, params)
            symbols = [dict(x) for x in cur.fetchall()]

    print_rows("CLOSED_TRADE_QUALITY_SUMMARY", summary)
    print_rows("CLOSED_TRADE_SUSPECT_BATCH", batches)
    print_rows("CLOSED_TRADE_QUALITY_SYMBOL", symbols)

    print("CLOSED_TRADE_QUALITY_AUDIT_V1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
