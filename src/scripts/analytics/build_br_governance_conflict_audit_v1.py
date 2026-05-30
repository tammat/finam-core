from __future__ import annotations

import argparse
import subprocess
from typing import Any

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


BR_SYMBOL_PATTERN = "^(BRM6@RTSX|BRN6@RTSX|BR_ROLLING@RTSX)$"


FINANCIAL_SQL = """
SELECT
    extract(hour from (coalesce(closed_at, exit_ts, created_at) AT TIME ZONE 'Europe/Moscow'))::int AS hour_msk,
    CASE
        WHEN side IN ('LONG', 'BUY') THEN 'BUY'
        WHEN side IN ('SHORT', 'SELL') THEN 'SELL'
        ELSE side
    END AS side,
    count(*) AS closed_trades,
    count(*) FILTER (WHERE net_pnl > 0) AS wins,
    count(*) FILTER (WHERE net_pnl <= 0) AS losses,
    round((count(*) FILTER (WHERE net_pnl > 0)::numeric / nullif(count(*), 0)), 6) AS winrate,
    round(sum(gross_pnl)::numeric, 6) AS gross_pnl,
    round(sum(net_pnl)::numeric, 6) AS net_pnl,
    round(avg(net_pnl)::numeric, 6) AS avg_net_pnl,
    round(sum(commission)::numeric, 6) AS commission,
    round(
        (
            sum(net_pnl) FILTER (WHERE net_pnl > 0)
            / nullif(abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)), 0)
        )::numeric,
        6
    ) AS profit_factor,
    min(coalesce(opened_at, entry_ts, created_at)) AS first_closed_trade_ts,
    max(coalesce(closed_at, exit_ts, created_at)) AS last_closed_trade_ts
FROM closed_trades
WHERE symbol ~ %(symbol_pattern)s
  AND coalesce(closed_at, exit_ts, created_at) >= now() - (%(window_days)s * interval '1 day')
  AND extract(hour from (coalesce(closed_at, exit_ts, created_at) AT TIME ZONE 'Europe/Moscow'))::int = %(hour)s
  AND CASE
        WHEN side IN ('LONG', 'BUY') THEN 'BUY'
        WHEN side IN ('SHORT', 'SELL') THEN 'SELL'
        ELSE side
      END = %(side)s
GROUP BY hour_msk, side;
"""


GOVERNANCE_SQL = """
SELECT
    hour_msk,
    side,
    count(*) AS governance_rows,
    count(*) FILTER (WHERE allowed = true) AS allowed_rows,
    count(*) FILTER (WHERE allowed = false) AS blocked_rows,
    round(avg(expectancy_points)::numeric, 6) AS avg_expectancy_points,
    min(expectancy_points) AS min_expectancy_points,
    max(expectancy_points) AS max_expectancy_points,
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
    min(created_at) AS first_governance_ts,
    max(created_at) AS last_governance_ts
FROM runtime_governance_live_accumulation_v1
WHERE symbol ~ %(symbol_pattern)s
  AND created_at >= now() - (%(window_days)s * interval '1 day')
  AND hour_msk = %(hour)s
  AND side = %(side)s
GROUP BY hour_msk, side;
"""


REASON_SQL = """
SELECT
    action,
    reason,
    session_action,
    strict_reason,
    decay_state,
    count(*) AS rows,
    count(*) FILTER (WHERE allowed = true) AS allowed_rows,
    count(*) FILTER (WHERE allowed = false) AS blocked_rows,
    round(avg(expectancy_points)::numeric, 6) AS avg_expectancy_points,
    min(expectancy_points) AS min_expectancy_points,
    max(expectancy_points) AS max_expectancy_points,
    min(created_at) AS first_event_ts,
    max(created_at) AS last_event_ts
FROM runtime_governance_live_accumulation_v1
WHERE symbol ~ %(symbol_pattern)s
  AND created_at >= now() - (%(window_days)s * interval '1 day')
  AND hour_msk = %(hour)s
  AND side = %(side)s
GROUP BY action, reason, session_action, strict_reason, decay_state
ORDER BY rows DESC, action, reason;
"""


SYMBOL_SQL = """
SELECT
    symbol,
    count(*) AS rows,
    count(*) FILTER (WHERE allowed = true) AS allowed_rows,
    count(*) FILTER (WHERE allowed = false) AS blocked_rows,
    round(avg(expectancy_points)::numeric, 6) AS avg_expectancy_points,
    min(created_at) AS first_event_ts,
    max(created_at) AS last_event_ts
FROM runtime_governance_live_accumulation_v1
WHERE symbol ~ %(symbol_pattern)s
  AND created_at >= now() - (%(window_days)s * interval '1 day')
  AND hour_msk = %(hour)s
  AND side = %(side)s
GROUP BY symbol
ORDER BY rows DESC, symbol;
"""


RECENT_FINANCIAL_SQL = """
SELECT
    count(*) AS recent_closed_trades,
    round(sum(net_pnl)::numeric, 6) AS recent_net_pnl,
    round(avg(net_pnl)::numeric, 6) AS recent_avg_net_pnl,
    min(coalesce(opened_at, entry_ts, created_at)) AS first_recent_trade_ts,
    max(coalesce(closed_at, exit_ts, created_at)) AS last_recent_trade_ts
FROM closed_trades
WHERE symbol ~ %(symbol_pattern)s
  AND coalesce(closed_at, exit_ts, created_at) >= now() - (%(recent_days)s * interval '1 day')
  AND extract(hour from (coalesce(closed_at, exit_ts, created_at) AT TIME ZONE 'Europe/Moscow'))::int = %(hour)s
  AND CASE
        WHEN side IN ('LONG', 'BUY') THEN 'BUY'
        WHEN side IN ('SHORT', 'SELL') THEN 'SELL'
        ELSE side
      END = %(side)s;
"""


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def fetch_one(conn: psycopg.Connection[Any], sql: str, params: dict[str, Any]) -> dict[str, Any]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else {}


def fetch_all(conn: psycopg.Connection[Any], sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


def print_row(prefix: str, row: dict[str, Any]) -> None:
    if not row:
        print(f"{prefix} empty=true", flush=True)
        return
    print(" ".join([prefix] + [f"{k}={v}" for k, v in row.items()]), flush=True)


def classify_root_cause(fin: dict[str, Any], gov: dict[str, Any], recent: dict[str, Any]) -> tuple[str, str]:
    closed_trades = int(fin.get("closed_trades") or 0)
    net_pnl = float(fin.get("net_pnl") or 0.0)
    pf_raw = fin.get("profit_factor")
    pf = float(pf_raw) if pf_raw is not None else None

    governance_rows = int(gov.get("governance_rows") or 0)
    blocked_rows = int(gov.get("blocked_rows") or 0)
    allowed_rows = int(gov.get("allowed_rows") or 0)
    gov_exp_raw = gov.get("avg_expectancy_points")
    gov_exp = float(gov_exp_raw) if gov_exp_raw is not None else None

    recent_trades = int(recent.get("recent_closed_trades") or 0)
    recent_pnl = float(recent.get("recent_net_pnl") or 0.0)

    if closed_trades == 0 and governance_rows > 0:
        return "WINDOW_MISMATCH", "governance_exists_but_no_closed_trades_in_window"

    if closed_trades > 0 and governance_rows == 0:
        return "WINDOW_MISMATCH", "closed_trades_exist_but_no_governance_events"

    if governance_rows < 10:
        return "SAMPLE_MISMATCH", "governance_sample_too_small"

    if recent_trades == 0 and closed_trades >= 20 and governance_rows >= 10:
        return "WINDOW_MISMATCH", "financial_history_old_governance_recent"

    if net_pnl > 0 and (pf is None or pf >= 1.0) and gov_exp is not None and gov_exp < 0 and blocked_rows > allowed_rows:
        if recent_trades > 0 and recent_pnl < 0:
            return "FINANCIAL_EDGE_DEGRADED", "historical_window_positive_recent_financial_negative_governance_negative"
        return "RULE_OVERBLOCKING", "financial_edge_positive_but_governance_blocks"

    if net_pnl < 0 and gov_exp is not None and gov_exp < 0 and blocked_rows > allowed_rows:
        return "GOVERNANCE_ALIGNED_WITH_LOSS", "financial_edge_negative_and_governance_negative"

    return "UNRESOLVED_CONFLICT", "mixed_or_insufficient_evidence"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hour", type=int, default=12)
    parser.add_argument("--side", default="BUY")
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument("--recent-days", type=int, default=7)
    args = parser.parse_args()

    params = {
        "symbol_pattern": BR_SYMBOL_PATTERN,
        "hour": args.hour,
        "side": args.side.upper(),
        "window_days": args.window_days,
        "recent_days": args.recent_days,
    }

    print("BR_GOVERNANCE_CONFLICT_AUDIT_V1", flush=True)
    print(
        "BR_GOVERNANCE_CONFLICT_AUDIT_CONFIG "
        f"hour={args.hour} side={args.side.upper()} "
        f"window_days={args.window_days} recent_days={args.recent_days} "
        f"git_clean={git_clean()}",
        flush=True,
    )

    with psycopg.connect(build_psycopg_url()) as conn:
        fin = fetch_one(conn, FINANCIAL_SQL, params)
        gov = fetch_one(conn, GOVERNANCE_SQL, params)
        recent = fetch_one(conn, RECENT_FINANCIAL_SQL, params)
        reasons = fetch_all(conn, REASON_SQL, params)
        symbols = fetch_all(conn, SYMBOL_SQL, params)

    print_row("BR_CONFLICT_FINANCIAL", fin)
    print_row("BR_CONFLICT_GOVERNANCE", gov)
    print_row("BR_CONFLICT_RECENT_FINANCIAL", recent)

    for row in reasons:
        print_row("BR_CONFLICT_REASON", row)

    for row in symbols:
        print_row("BR_CONFLICT_SYMBOL", row)

    root, reason = classify_root_cause(fin, gov, recent)
    print(
        "BR_CONFLICT_ROOT_CAUSE "
        f"root_cause={root} "
        f"reason={reason}",
        flush=True,
    )

    print("BR_GOVERNANCE_CONFLICT_AUDIT_V1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
