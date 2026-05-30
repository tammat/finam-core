from __future__ import annotations

import argparse
import subprocess
from typing import Any

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


BR_SYMBOL_PATTERN = "^(BRM6@RTSX|BRN6@RTSX|BR_ROLLING@RTSX)$"


TOTAL_SQL = """
SELECT
    count(*) AS trades,
    round(sum(gross_pnl)::numeric, 6) AS gross_pnl,
    round(sum(net_pnl)::numeric, 6) AS net_pnl,
    round(avg(net_pnl)::numeric, 6) AS expectancy,
    round(sum(commission)::numeric, 6) AS commission,
    min(coalesce(opened_at, entry_ts, created_at)) AS first_trade,
    max(coalesce(closed_at, exit_ts, created_at)) AS last_trade
FROM closed_trades
WHERE symbol ~ %(symbol_pattern)s
  AND coalesce(closed_at, exit_ts, created_at) >= now() - (%(window_days)s * interval '1 day');
"""


DIRECTION_SQL = """
SELECT
    symbol,
    side,
    count(*) AS trades,
    count(*) FILTER (WHERE net_pnl > 0) AS wins,
    count(*) FILTER (WHERE net_pnl <= 0) AS losses,
    round((count(*) FILTER (WHERE net_pnl > 0)::numeric / nullif(count(*), 0)), 6) AS winrate,
    round(sum(gross_pnl)::numeric, 6) AS gross_pnl,
    round(sum(net_pnl)::numeric, 6) AS net_pnl,
    round(avg(net_pnl)::numeric, 6) AS expectancy,
    round(
        (
            sum(net_pnl) FILTER (WHERE net_pnl > 0)
            / nullif(abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)), 0)
        )::numeric,
        6
    ) AS profit_factor,
    round(sum(commission)::numeric, 6) AS commission,
    max(coalesce(closed_at, exit_ts, created_at)) AS last_closed
FROM closed_trades
WHERE symbol ~ %(symbol_pattern)s
  AND coalesce(closed_at, exit_ts, created_at) >= now() - (%(window_days)s * interval '1 day')
GROUP BY symbol, side
ORDER BY net_pnl ASC, trades DESC;
"""


HOUR_SQL = """
SELECT
    extract(hour from (coalesce(closed_at, exit_ts, created_at) AT TIME ZONE 'Europe/Moscow'))::int AS hour_msk,
    side,
    count(*) AS trades,
    count(*) FILTER (WHERE net_pnl > 0) AS wins,
    count(*) FILTER (WHERE net_pnl <= 0) AS losses,
    round((count(*) FILTER (WHERE net_pnl > 0)::numeric / nullif(count(*), 0)), 6) AS winrate,
    round(sum(net_pnl)::numeric, 6) AS net_pnl,
    round(avg(net_pnl)::numeric, 6) AS expectancy,
    round(
        (
            sum(net_pnl) FILTER (WHERE net_pnl > 0)
            / nullif(abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)), 0)
        )::numeric,
        6
    ) AS profit_factor,
    round(sum(commission)::numeric, 6) AS commission,
    max(coalesce(closed_at, exit_ts, created_at)) AS last_closed
FROM closed_trades
WHERE symbol ~ %(symbol_pattern)s
  AND coalesce(closed_at, exit_ts, created_at) >= now() - (%(window_days)s * interval '1 day')
GROUP BY hour_msk, side
ORDER BY net_pnl ASC, trades DESC;
"""


REGIME_SQL = """
SELECT
    coalesce(nullif(entry_regime, ''), nullif(regime, ''), 'unknown') AS regime_key,
    side,
    count(*) AS trades,
    count(*) FILTER (WHERE net_pnl > 0) AS wins,
    count(*) FILTER (WHERE net_pnl <= 0) AS losses,
    round((count(*) FILTER (WHERE net_pnl > 0)::numeric / nullif(count(*), 0)), 6) AS winrate,
    round(sum(net_pnl)::numeric, 6) AS net_pnl,
    round(avg(net_pnl)::numeric, 6) AS expectancy,
    round(
        (
            sum(net_pnl) FILTER (WHERE net_pnl > 0)
            / nullif(abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)), 0)
        )::numeric,
        6
    ) AS profit_factor,
    round(sum(commission)::numeric, 6) AS commission
FROM closed_trades
WHERE symbol ~ %(symbol_pattern)s
  AND coalesce(closed_at, exit_ts, created_at) >= now() - (%(window_days)s * interval '1 day')
GROUP BY regime_key, side
ORDER BY net_pnl ASC, trades DESC;
"""


GOVERNANCE_HOUR_SQL = """
SELECT
    hour_msk,
    side,
    count(*) AS governance_rows,
    count(*) FILTER (WHERE allowed = true) AS allowed_rows,
    count(*) FILTER (WHERE allowed = false) AS blocked_rows,
    round(avg(expectancy_points)::numeric, 6) AS avg_expectancy_points,
    coalesce(sum(
        CASE
            WHEN allowed = false AND expectancy_points < 0
            THEN abs(expectancy_points)
            ELSE 0
        END
    ), 0)::float AS saved_loss_points,
    coalesce(sum(
        CASE
            WHEN allowed = false AND expectancy_points > 0
            THEN expectancy_points
            ELSE 0
        END
    ), 0)::float AS missed_profit_points,
    max(created_at) AS last_event_ts
FROM runtime_governance_live_accumulation_v1
WHERE symbol ~ %(symbol_pattern)s
  AND created_at >= now() - (%(window_days)s * interval '1 day')
GROUP BY hour_msk, side
ORDER BY saved_loss_points DESC, governance_rows DESC;
"""


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def rows(conn: psycopg.Connection[Any], sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def print_row(prefix: str, row: dict[str, Any]) -> None:
    parts = [prefix]
    for key, value in row.items():
        parts.append(f"{key}={value}")
    print(" ".join(parts), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-days", type=int, default=30)
    args = parser.parse_args()

    params = {
        "symbol_pattern": BR_SYMBOL_PATTERN,
        "window_days": args.window_days,
    }

    print("BR_LOSS_DECOMPOSITION_V1", flush=True)
    print(
        f"BR_LOSS_DECOMPOSITION_CONFIG window_days={args.window_days} git_clean={git_clean()}",
        flush=True,
    )

    with psycopg.connect(build_psycopg_url()) as conn:
        total = rows(conn, TOTAL_SQL, params)
        for row in total:
            print_row("BR_LOSS_TOTAL", row)

        direction_rows = rows(conn, DIRECTION_SQL, params)
        for row in direction_rows:
            print_row("BR_LOSS_DIRECTION", row)

        hour_rows = rows(conn, HOUR_SQL, params)
        for row in hour_rows:
            print_row("BR_LOSS_HOUR", row)

        regime_rows = rows(conn, REGIME_SQL, params)
        for row in regime_rows:
            print_row("BR_LOSS_REGIME", row)

        governance_rows = rows(conn, GOVERNANCE_HOUR_SQL, params)
        for row in governance_rows:
            print_row("BR_GOVERNANCE_HOUR_OVERLAY", row)

    print("BR_LOSS_DECOMPOSITION_V1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
