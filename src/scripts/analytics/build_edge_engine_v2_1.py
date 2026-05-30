from __future__ import annotations

import argparse
import subprocess
from typing import Any

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


EDGE_SQL = """
SELECT
    symbol,
    strategy,
    timeframe,
    origin,
    side,
    extract(hour from (entry_ts AT TIME ZONE 'Europe/Moscow'))::int AS hour_msk,
    count(*) AS trades,
    count(*) FILTER (WHERE net_pnl > 0) AS wins,
    count(*) FILTER (WHERE net_pnl <= 0) AS losses,
    round((count(*) FILTER (WHERE net_pnl > 0)::numeric / nullif(count(*), 0)), 6) AS winrate,
    round(sum(net_pnl)::numeric, 6) AS net_pnl,
    round(avg(net_pnl)::numeric, 6) AS expectancy,
    round((
        sum(net_pnl) FILTER (WHERE net_pnl > 0)
        / nullif(abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)), 0)
    )::numeric, 6) AS profit_factor,
    round(max(net_pnl)::numeric, 6) AS best_trade,
    round(min(net_pnl)::numeric, 6) AS worst_trade,
    round(avg(holding_seconds)::numeric, 2) AS avg_holding_seconds,
    min(entry_ts) AS first_entry,
    max(exit_ts) AS last_exit
FROM analytics_strategy_trades_v2
GROUP BY symbol, strategy, timeframe, origin, side, hour_msk
HAVING count(*) >= %(min_trades)s
ORDER BY net_pnl DESC, trades DESC;
"""


def git_clean() -> bool:
    r = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, check=False)
    return r.stdout.strip() == ""


def classify(row: dict[str, Any], min_pf: float, min_expectancy: float) -> tuple[str, str]:
    origin = str(row.get("origin") or "")
    pf = row.get("profit_factor")
    expectancy = float(row.get("expectancy") or 0.0)
    net_pnl = float(row.get("net_pnl") or 0.0)

    if origin in {"replay_br_pipeline", "historical_signal_replay"}:
        if pf is not None and float(pf) >= min_pf and expectancy > min_expectancy and net_pnl > 0:
            return "REPLAY_SEGMENT_EDGE", "positive_segment_but_replay_only"
        if net_pnl <= 0 or expectancy <= 0:
            return "REPLAY_SEGMENT_NEGATIVE", "negative_replay_segment"
        return "REPLAY_SEGMENT_OBSERVE", "weak_replay_segment"

    if pf is not None and float(pf) >= min_pf and expectancy > min_expectancy and net_pnl > 0:
        return "PRODUCTION_LIKE_SEGMENT_EDGE", "positive_segment"

    if net_pnl <= 0 or expectancy <= 0:
        return "SEGMENT_NO_EDGE", "negative_or_zero_segment"

    return "SEGMENT_OBSERVE", "positive_but_below_threshold"


def score(row: dict[str, Any]) -> float:
    trades = float(row.get("trades") or 0.0)
    pf = float(row.get("profit_factor") or 0.0)
    expectancy = float(row.get("expectancy") or 0.0)
    winrate = float(row.get("winrate") or 0.0)

    sample_score = min(trades / 30.0, 1.0)
    pf_score = min(pf / 2.0, 1.5)
    expectancy_score = max(min(expectancy, 5.0), -5.0) / 5.0

    return round(
        0.30 * sample_score
        + 0.30 * pf_score
        + 0.30 * expectancy_score
        + 0.10 * winrate,
        6,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-trades", type=int, default=5)
    parser.add_argument("--min-pf", type=float, default=1.20)
    parser.add_argument("--min-expectancy", type=float, default=0.0)
    args = parser.parse_args()

    print("EDGE_ENGINE_V2_1", flush=True)
    print(
        "EDGE_ENGINE_V2_1_CONFIG "
        f"min_trades={args.min_trades} "
        f"min_pf={args.min_pf} "
        f"min_expectancy={args.min_expectancy} "
        f"git_clean={git_clean()}",
        flush=True,
    )

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(EDGE_SQL, {"min_trades": args.min_trades})
            rows = [dict(x) for x in cur.fetchall()]

    summary: dict[str, int] = {}

    for row in rows:
        verdict, reason = classify(row, args.min_pf, args.min_expectancy)
        edge_score = score(row)
        summary[verdict] = summary.get(verdict, 0) + 1

        print(
            " ".join(
                ["EDGE_ENGINE_V2_1_ROW"]
                + [f"{k}={v}" for k, v in row.items()]
                + [
                    f"edge_score={edge_score}",
                    f"verdict={verdict}",
                    f"reason={reason}",
                ]
            ),
            flush=True,
        )

    for verdict, count in sorted(summary.items()):
        print(f"EDGE_ENGINE_V2_1_SUMMARY verdict={verdict} rows={count}", flush=True)

    print("EDGE_ENGINE_V2_1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
