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
WITH base AS (
    SELECT
        *,
        CASE
            WHEN entry_price > 0 AND exit_price > 0
            THEN abs(exit_price / entry_price - 1)
            ELSE NULL
        END AS move_ratio,
        CASE
            WHEN entry_price > 0 AND exit_price > 0
                 AND abs(exit_price / entry_price - 1) > %(outlier_pct)s
            THEN true
            ELSE false
        END AS is_outlier
    FROM closed_trades
    WHERE coalesce(closed_at, exit_ts, created_at) >= now() - (%(window_days)s * interval '1 day')
)
SELECT
    symbol,
    count(*) AS closed_trades,
    count(*) FILTER (WHERE is_outlier) AS outlier_trades,
    round(
        (count(*) FILTER (WHERE is_outlier)::numeric / nullif(count(*), 0)),
        6
    ) AS outlier_rate,
    round(sum(net_pnl)::numeric, 6) AS total_net_pnl,
    round(sum(net_pnl) FILTER (WHERE is_outlier)::numeric, 6) AS outlier_net_pnl,
    round(sum(net_pnl) FILTER (WHERE NOT is_outlier)::numeric, 6) AS clean_net_pnl,
    round(max(move_ratio)::numeric, 6) AS max_move_ratio,
    min(coalesce(closed_at, exit_ts, created_at)) AS first_trade,
    max(coalesce(closed_at, exit_ts, created_at)) AS last_trade
FROM base
GROUP BY symbol
HAVING count(*) FILTER (WHERE is_outlier) > 0
ORDER BY abs(coalesce(sum(net_pnl) FILTER (WHERE is_outlier), 0)) DESC, outlier_trades DESC, symbol
LIMIT %(limit_symbols)s;
"""


DETAIL_SQL = """
WITH base AS (
    SELECT
        id,
        signal_id,
        symbol,
        side,
        entry_price,
        exit_price,
        qty,
        gross_pnl,
        net_pnl,
        commission,
        coalesce(opened_at, entry_ts, created_at) AS opened_ts,
        coalesce(closed_at, exit_ts, created_at) AS closed_ts,
        CASE
            WHEN entry_price > 0 AND exit_price > 0
            THEN abs(exit_price / entry_price - 1)
            ELSE NULL
        END AS move_ratio,
        payload
    FROM closed_trades
    WHERE coalesce(closed_at, exit_ts, created_at) >= now() - (%(window_days)s * interval '1 day')
)
SELECT
    id,
    symbol,
    side,
    round(entry_price::numeric, 8) AS entry_price,
    round(exit_price::numeric, 8) AS exit_price,
    qty,
    round(gross_pnl::numeric, 6) AS gross_pnl,
    round(net_pnl::numeric, 6) AS net_pnl,
    round(commission::numeric, 6) AS commission,
    round(move_ratio::numeric, 6) AS move_ratio,
    opened_ts,
    closed_ts,
    signal_id,
    payload->>'root_symbol' AS root_symbol,
    payload->>'continuous_symbol' AS continuous_symbol,
    payload->>'futures_month_code' AS futures_month_code,
    payload->>'futures_year_code' AS futures_year_code
FROM base
WHERE move_ratio > %(outlier_pct)s
ORDER BY abs(net_pnl) DESC, move_ratio DESC
LIMIT %(limit_trades)s;
"""


CLEAN_EDGE_SQL = """
WITH base AS (
    SELECT
        *,
        CASE
            WHEN entry_price > 0 AND exit_price > 0
                 AND abs(exit_price / entry_price - 1) > %(outlier_pct)s
            THEN true
            ELSE false
        END AS is_outlier
    FROM closed_trades
    WHERE coalesce(closed_at, exit_ts, created_at) >= now() - (%(window_days)s * interval '1 day')
)
SELECT
    symbol,
    count(*) AS closed_trades,
    count(*) FILTER (WHERE NOT is_outlier) AS clean_trades,
    count(*) FILTER (WHERE is_outlier) AS outlier_trades,
    round(sum(net_pnl)::numeric, 6) AS total_net_pnl,
    round(sum(net_pnl) FILTER (WHERE NOT is_outlier)::numeric, 6) AS clean_net_pnl,
    round(avg(net_pnl) FILTER (WHERE NOT is_outlier)::numeric, 6) AS clean_avg_net_pnl,
    round((
        sum(net_pnl) FILTER (WHERE NOT is_outlier AND net_pnl > 0)
        /
        nullif(abs(sum(net_pnl) FILTER (WHERE NOT is_outlier AND net_pnl < 0)), 0)
    )::numeric, 6) AS clean_profit_factor,
    round(
        (
            count(*) FILTER (WHERE NOT is_outlier AND net_pnl > 0)::numeric
            / nullif(count(*) FILTER (WHERE NOT is_outlier), 0)
        ),
        6
    ) AS clean_winrate
FROM base
GROUP BY symbol
HAVING count(*) >= %(min_trades)s
ORDER BY clean_net_pnl DESC NULLS LAST, clean_profit_factor DESC NULLS LAST
LIMIT %(limit_symbols)s;
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-days", type=int, default=365)
    parser.add_argument("--outlier-pct", type=float, default=0.20)
    parser.add_argument("--min-trades", type=int, default=20)
    parser.add_argument("--limit-symbols", type=int, default=50)
    parser.add_argument("--limit-trades", type=int, default=100)
    args = parser.parse_args()

    params = {
        "window_days": args.window_days,
        "outlier_pct": args.outlier_pct,
        "min_trades": args.min_trades,
        "limit_symbols": args.limit_symbols,
        "limit_trades": args.limit_trades,
    }

    print("GLOBAL_OUTLIER_AUDIT_V1", flush=True)
    print(
        "GLOBAL_OUTLIER_AUDIT_CONFIG "
        f"window_days={args.window_days} "
        f"outlier_pct={args.outlier_pct} "
        f"min_trades={args.min_trades} "
        f"git_clean={git_clean()}",
        flush=True,
    )

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(SUMMARY_SQL, params)
            summary = [dict(row) for row in cur.fetchall()]

            cur.execute(DETAIL_SQL, params)
            details = [dict(row) for row in cur.fetchall()]

            cur.execute(CLEAN_EDGE_SQL, params)
            clean = [dict(row) for row in cur.fetchall()]

    print_rows("GLOBAL_OUTLIER_SUMMARY", summary)
    print_rows("GLOBAL_OUTLIER_TRADE", details)
    print_rows("GLOBAL_CLEAN_EDGE", clean)

    total_outlier_trades = sum(int(row.get("outlier_trades") or 0) for row in summary)
    total_outlier_pnl = sum(float(row.get("outlier_net_pnl") or 0.0) for row in summary)

    print(
        "GLOBAL_OUTLIER_VERDICT "
        f"outlier_symbols={len(summary)} "
        f"outlier_trades={total_outlier_trades} "
        f"outlier_net_pnl={round(total_outlier_pnl, 6)} "
        f"status={'DATA_QUALITY_RISK' if total_outlier_trades > 0 else 'NO_OUTLIERS_FOUND'}",
        flush=True,
    )

    print("GLOBAL_OUTLIER_AUDIT_V1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
