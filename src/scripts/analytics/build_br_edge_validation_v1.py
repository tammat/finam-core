from __future__ import annotations

import argparse
import subprocess
from typing import Any

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


BR_SYMBOL_PATTERN = "^(BRM6@RTSX|BRN6@RTSX|BR_ROLLING@RTSX)$"


def git_clean() -> bool:
    result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, check=False)
    return result.stdout.strip() == ""


def print_rows(prefix: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        print(f"{prefix} empty=true", flush=True)
        return

    for row in rows:
        print(" ".join([prefix] + [f"{k}={v}" for k, v in row.items()]), flush=True)


TOTAL_SQL = """
SELECT
    count(*) AS trades,
    count(*) FILTER (WHERE net_pnl > 0) AS wins,
    count(*) FILTER (WHERE net_pnl <= 0) AS losses,
    round((count(*) FILTER (WHERE net_pnl > 0)::numeric / nullif(count(*), 0)), 6) AS winrate,
    round((
        sum(net_pnl) FILTER (WHERE net_pnl > 0)
        / nullif(abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)), 0)
    )::numeric, 6) AS profit_factor,
    round(sum(gross_pnl)::numeric, 6) AS gross_pnl,
    round(sum(net_pnl)::numeric, 6) AS net_pnl,
    round(avg(net_pnl)::numeric, 6) AS avg_net_pnl,
    round(sum(commission)::numeric, 6) AS commission,
    min(coalesce(opened_at, entry_ts, created_at)) AS first_trade,
    max(coalesce(closed_at, exit_ts, created_at)) AS last_trade
FROM closed_trades
WHERE symbol ~ %(symbol_pattern)s
  AND coalesce(closed_at, exit_ts, created_at) >= now() - (%(window_days)s * interval '1 day');
"""


OUTLIER_SQL = """
SELECT
    count(*) AS total_trades,
    count(*) FILTER (
        WHERE entry_price > 0
          AND exit_price > 0
          AND abs(exit_price / entry_price - 1) > %(outlier_pct)s
    ) AS outlier_trades,
    round(sum(net_pnl)::numeric, 6) AS total_net_pnl,
    round(sum(net_pnl) FILTER (
        WHERE entry_price > 0
          AND exit_price > 0
          AND abs(exit_price / entry_price - 1) > %(outlier_pct)s
    )::numeric, 6) AS outlier_net_pnl,
    round(sum(net_pnl) FILTER (
        WHERE entry_price > 0
          AND exit_price > 0
          AND abs(exit_price / entry_price - 1) <= %(outlier_pct)s
    )::numeric, 6) AS clean_net_pnl
FROM closed_trades
WHERE symbol ~ %(symbol_pattern)s
  AND coalesce(closed_at, exit_ts, created_at) >= now() - (%(window_days)s * interval '1 day');
"""


CLEAN_TOTAL_SQL = """
SELECT
    count(*) AS clean_trades,
    count(*) FILTER (WHERE net_pnl > 0) AS clean_wins,
    count(*) FILTER (WHERE net_pnl <= 0) AS clean_losses,
    round((count(*) FILTER (WHERE net_pnl > 0)::numeric / nullif(count(*), 0)), 6) AS clean_winrate,
    round((
        sum(net_pnl) FILTER (WHERE net_pnl > 0)
        / nullif(abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)), 0)
    )::numeric, 6) AS clean_profit_factor,
    round(sum(net_pnl)::numeric, 6) AS clean_net_pnl,
    round(avg(net_pnl)::numeric, 6) AS clean_avg_net_pnl
FROM closed_trades
WHERE symbol ~ %(symbol_pattern)s
  AND coalesce(closed_at, exit_ts, created_at) >= now() - (%(window_days)s * interval '1 day')
  AND entry_price > 0
  AND exit_price > 0
  AND abs(exit_price / entry_price - 1) <= %(outlier_pct)s;
"""


BY_HOUR_SQL = """
SELECT
    extract(hour from (coalesce(closed_at, exit_ts, created_at) AT TIME ZONE 'Europe/Moscow'))::int AS hour_msk,
    CASE
        WHEN side IN ('LONG', 'BUY') THEN 'BUY'
        WHEN side IN ('SHORT', 'SELL') THEN 'SELL'
        ELSE side
    END AS side,
    count(*) AS trades,
    count(*) FILTER (WHERE net_pnl > 0) AS wins,
    count(*) FILTER (WHERE net_pnl <= 0) AS losses,
    round((count(*) FILTER (WHERE net_pnl > 0)::numeric / nullif(count(*), 0)), 6) AS winrate,
    round((
        sum(net_pnl) FILTER (WHERE net_pnl > 0)
        / nullif(abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)), 0)
    )::numeric, 6) AS profit_factor,
    round(sum(net_pnl)::numeric, 6) AS net_pnl,
    round(avg(net_pnl)::numeric, 6) AS avg_net_pnl
FROM closed_trades
WHERE symbol ~ %(symbol_pattern)s
  AND coalesce(closed_at, exit_ts, created_at) >= now() - (%(window_days)s * interval '1 day')
  AND entry_price > 0
  AND exit_price > 0
  AND abs(exit_price / entry_price - 1) <= %(outlier_pct)s
GROUP BY hour_msk, side
ORDER BY net_pnl ASC;
"""


BY_SIDE_SQL = """
SELECT
    CASE
        WHEN side IN ('LONG', 'BUY') THEN 'BUY'
        WHEN side IN ('SHORT', 'SELL') THEN 'SELL'
        ELSE side
    END AS side,
    count(*) AS trades,
    count(*) FILTER (WHERE net_pnl > 0) AS wins,
    count(*) FILTER (WHERE net_pnl <= 0) AS losses,
    round((count(*) FILTER (WHERE net_pnl > 0)::numeric / nullif(count(*), 0)), 6) AS winrate,
    round((
        sum(net_pnl) FILTER (WHERE net_pnl > 0)
        / nullif(abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)), 0)
    )::numeric, 6) AS profit_factor,
    round(sum(net_pnl)::numeric, 6) AS net_pnl,
    round(avg(net_pnl)::numeric, 6) AS avg_net_pnl
FROM closed_trades
WHERE symbol ~ %(symbol_pattern)s
  AND coalesce(closed_at, exit_ts, created_at) >= now() - (%(window_days)s * interval '1 day')
  AND entry_price > 0
  AND exit_price > 0
  AND abs(exit_price / entry_price - 1) <= %(outlier_pct)s
GROUP BY side
ORDER BY net_pnl DESC;
"""


def verdict(clean: dict[str, Any], outlier: dict[str, Any]) -> tuple[str, str]:
    clean_trades = int(clean.get("clean_trades") or 0)
    clean_pnl = float(clean.get("clean_net_pnl") or 0.0)
    clean_pf_raw = clean.get("clean_profit_factor")
    clean_pf = float(clean_pf_raw) if clean_pf_raw is not None else 0.0
    outliers = int(outlier.get("outlier_trades") or 0)

    if clean_trades < 50:
        return "INSUFFICIENT_SAMPLE", "clean_trades_below_50"

    if outliers > 0:
        return "DATA_QUALITY_WARNING", "outliers_present_edge_requires_clean_view"

    if clean_pnl > 0 and clean_pf >= 1.10:
        return "EDGE_CANDIDATE", "clean_pnl_positive_pf_above_1_10"

    if clean_pnl <= 0 or clean_pf < 1.0:
        return "NO_EDGE", "clean_pnl_or_pf_not_positive"

    return "OBSERVE", "weak_or_mixed_edge"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument("--outlier-pct", type=float, default=0.20)
    args = parser.parse_args()

    params = {
        "symbol_pattern": BR_SYMBOL_PATTERN,
        "window_days": args.window_days,
        "outlier_pct": args.outlier_pct,
    }

    print("BR_EDGE_VALIDATION_V1", flush=True)
    print(
        f"BR_EDGE_VALIDATION_CONFIG window_days={args.window_days} "
        f"outlier_pct={args.outlier_pct} git_clean={git_clean()}",
        flush=True,
    )

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(TOTAL_SQL, params)
            total = dict(cur.fetchone() or {})
            cur.execute(OUTLIER_SQL, params)
            outlier = dict(cur.fetchone() or {})
            cur.execute(CLEAN_TOTAL_SQL, params)
            clean = dict(cur.fetchone() or {})
            cur.execute(BY_HOUR_SQL, params)
            by_hour = [dict(x) for x in cur.fetchall()]
            cur.execute(BY_SIDE_SQL, params)
            by_side = [dict(x) for x in cur.fetchall()]

    print_rows("BR_EDGE_TOTAL", [total])
    print_rows("BR_EDGE_OUTLIER", [outlier])
    print_rows("BR_EDGE_CLEAN_TOTAL", [clean])
    print_rows("BR_EDGE_BY_HOUR", by_hour)
    print_rows("BR_EDGE_BY_SIDE", by_side)

    status, reason = verdict(clean, outlier)
    print(f"BR_EDGE_VERDICT status={status} reason={reason}", flush=True)
    print("BR_EDGE_VALIDATION_V1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
