from __future__ import annotations

import argparse
import subprocess
from typing import Any

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


BR_SYMBOL_PATTERN = "^(BRM6@RTSX|BRN6@RTSX|BR_ROLLING@RTSX)$"


POLICY_SQL = """
WITH closed_by_hour AS (
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
        sum(net_pnl) AS net_pnl_sum,
        avg(net_pnl) AS avg_net_pnl,
        sum(commission) AS commission_sum,
        (
            sum(net_pnl) FILTER (WHERE net_pnl > 0)
            / nullif(abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)), 0)
        ) AS profit_factor,
        max(coalesce(closed_at, exit_ts, created_at)) AS last_closed
    FROM closed_trades
    WHERE symbol ~ %(symbol_pattern)s
      AND coalesce(closed_at, exit_ts, created_at) >= now() - (%(window_days)s * interval '1 day')
    GROUP BY hour_msk, side
),
gov_by_hour AS (
    SELECT
        hour_msk,
        side,
        count(*) AS governance_rows,
        count(*) FILTER (WHERE allowed = true) AS allowed_rows,
        count(*) FILTER (WHERE allowed = false) AS blocked_rows,
        avg(expectancy_points) AS avg_governance_expectancy,
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
        max(created_at) AS last_governance_ts
    FROM runtime_governance_live_accumulation_v1
    WHERE symbol ~ %(symbol_pattern)s
      AND created_at >= now() - (%(window_days)s * interval '1 day')
    GROUP BY hour_msk, side
),
joined AS (
    SELECT
        coalesce(c.hour_msk, g.hour_msk) AS hour_msk,
        coalesce(c.side, g.side) AS side,
        coalesce(c.closed_trades, 0) AS closed_trades,
        coalesce(c.wins, 0) AS wins,
        coalesce(c.losses, 0) AS losses,
        c.net_pnl_sum,
        c.avg_net_pnl,
        c.profit_factor,
        c.commission_sum,
        c.last_closed,
        coalesce(g.governance_rows, 0) AS governance_rows,
        coalesce(g.allowed_rows, 0) AS allowed_rows,
        coalesce(g.blocked_rows, 0) AS blocked_rows,
        g.avg_governance_expectancy,
        coalesce(g.saved_loss_points, 0) AS saved_loss_points,
        coalesce(g.missed_profit_points, 0) AS missed_profit_points,
        g.last_governance_ts
    FROM closed_by_hour c
    FULL OUTER JOIN gov_by_hour g
      ON g.hour_msk = c.hour_msk
     AND g.side = c.side
)
SELECT
    hour_msk,
    side,
    closed_trades,
    wins,
    losses,
    round((wins::numeric / nullif(closed_trades, 0)), 6) AS winrate,
    round(net_pnl_sum::numeric, 6) AS net_pnl_sum,
    round(avg_net_pnl::numeric, 6) AS avg_net_pnl,
    round(profit_factor::numeric, 6) AS profit_factor,
    round(commission_sum::numeric, 6) AS commission_sum,
    governance_rows,
    allowed_rows,
    blocked_rows,
    round(avg_governance_expectancy::numeric, 6) AS avg_governance_expectancy,
    round(saved_loss_points::numeric, 6) AS saved_loss_points,
    round(missed_profit_points::numeric, 6) AS missed_profit_points,
    last_closed,
    last_governance_ts
FROM joined
ORDER BY hour_msk, side;
"""


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def sample_quality(closed_trades: int, governance_rows: int) -> str:
    total = max(closed_trades, governance_rows)
    if total <= 0:
        return "NO_DATA"
    if total < 5:
        return "TOO_SMALL"
    if total < 20:
        return "EARLY"
    if total < 50:
        return "BUILDING"
    if total < 100:
        return "GOOD"
    return "STRONG"


def classify_policy(row: dict[str, Any], *, min_closed_trades: int, min_governance_rows: int) -> tuple[str, str, str]:
    closed_trades = int(row.get("closed_trades") or 0)
    governance_rows = int(row.get("governance_rows") or 0)
    net_pnl = float(row.get("net_pnl_sum") or 0.0)
    avg_net = float(row.get("avg_net_pnl") or 0.0)
    pf_raw = row.get("profit_factor")
    pf = float(pf_raw) if pf_raw is not None else None
    gov_exp_raw = row.get("avg_governance_expectancy")
    gov_exp = float(gov_exp_raw) if gov_exp_raw is not None else None
    blocked_rows = int(row.get("blocked_rows") or 0)
    allowed_rows = int(row.get("allowed_rows") or 0)
    saved_loss = float(row.get("saved_loss_points") or 0.0)
    missed_profit = float(row.get("missed_profit_points") or 0.0)

    quality = sample_quality(closed_trades, governance_rows)

    enough_closed = closed_trades >= min_closed_trades
    enough_gov = governance_rows >= min_governance_rows

    # Русский комментарий:
    # v2.1: отдельный безопасный флаг риска.
    # Это НЕ execution block, а только аналитическая маркировка опасного окна.
    severe_financial_loss = (
        closed_trades >= 10
        and net_pnl <= -20.0
        and avg_net < 0
        and pf is not None
        and pf < 0.5
    )

    if severe_financial_loss and not enough_gov:
        return "HIGH_RISK_OBSERVE", quality, "financial_loss_severe_but_governance_sample_low"

    if severe_financial_loss and enough_gov and (gov_exp is None or gov_exp < 0):
        return "HIGH_RISK_OBSERVE", quality, "financial_loss_severe_and_governance_not_positive"

    if enough_closed and enough_gov:
        if net_pnl > 0 and avg_net > 0 and (pf is None or pf >= 1.05) and (gov_exp is None or gov_exp > 0):
            return "ALLOW", quality, "financial_edge_positive_and_governance_positive"

        if net_pnl < 0 and avg_net < 0 and gov_exp is not None and gov_exp < 0 and blocked_rows > allowed_rows:
            if saved_loss > max(0.25, missed_profit * 2):
                return "SOFT_BLOCK", quality, "financial_edge_negative_and_governance_saved_loss_positive"
            return "OBSERVE", quality, "negative_edge_but_saved_loss_not_strong"

        if net_pnl > 0 and gov_exp is not None and gov_exp < 0:
            return "OBSERVE", quality, "conflict_financial_positive_governance_negative"

        if net_pnl < 0 and gov_exp is not None and gov_exp > 0:
            return "OBSERVE", quality, "conflict_financial_negative_governance_positive"

    if enough_gov and not enough_closed:
        if gov_exp is not None and gov_exp > 0 and allowed_rows > blocked_rows:
            return "OBSERVE", quality, "governance_positive_but_closed_sample_missing"
        if gov_exp is not None and gov_exp < 0 and blocked_rows > allowed_rows:
            return "OBSERVE", quality, "governance_negative_but_closed_sample_missing"

    if enough_closed and not enough_gov:
        if net_pnl > 0 and avg_net > 0:
            return "OBSERVE", quality, "financial_positive_but_governance_sample_missing"
        if net_pnl < 0 and avg_net < 0:
            return "OBSERVE", quality, "financial_negative_but_governance_sample_missing"

    return "OBSERVE", quality, "insufficient_or_conflicting_evidence"


def print_policy(row: dict[str, Any], action: str, quality: str, reason: str) -> None:
    parts = [
        "BR_POLICY_CANDIDATE",
        f"hour_msk={row.get('hour_msk')}",
        f"side={row.get('side')}",
        f"action={action}",
        f"sample_quality={quality}",
        f"closed_trades={row.get('closed_trades')}",
        f"net_pnl_sum={row.get('net_pnl_sum')}",
        f"avg_net_pnl={row.get('avg_net_pnl')}",
        f"profit_factor={row.get('profit_factor')}",
        f"governance_rows={row.get('governance_rows')}",
        f"allowed_rows={row.get('allowed_rows')}",
        f"blocked_rows={row.get('blocked_rows')}",
        f"avg_governance_expectancy={row.get('avg_governance_expectancy')}",
        f"saved_loss_points={row.get('saved_loss_points')}",
        f"missed_profit_points={row.get('missed_profit_points')}",
        f"reason={reason}",
    ]
    print(" ".join(parts), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument("--min-closed-trades", type=int, default=5)
    parser.add_argument("--min-governance-rows", type=int, default=5)
    args = parser.parse_args()

    params = {
        "symbol_pattern": BR_SYMBOL_PATTERN,
        "window_days": args.window_days,
    }

    print("BR_GOVERNANCE_ALPHA_V2_1", flush=True)
    print(
        "BR_GOVERNANCE_ALPHA_V2_1_CONFIG "
        f"window_days={args.window_days} "
        f"min_closed_trades={args.min_closed_trades} "
        f"min_governance_rows={args.min_governance_rows} "
        f"git_clean={git_clean()}",
        flush=True,
    )

    counters: dict[str, int] = {}

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(POLICY_SQL, params)
            rows = list(cur.fetchall())

    for row in rows:
        action, quality, reason = classify_policy(
            row,
            min_closed_trades=args.min_closed_trades,
            min_governance_rows=args.min_governance_rows,
        )
        counters[action] = counters.get(action, 0) + 1
        print_policy(row, action, quality, reason)

    for action, count in sorted(counters.items()):
        print(f"BR_POLICY_SUMMARY action={action} rows={count}", flush=True)

    print("BR_GOVERNANCE_ALPHA_V2_1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
