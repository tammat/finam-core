from __future__ import annotations

import argparse
import re
import subprocess
from typing import Any

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


FUTURES_PREFIX_MAP = {
    "BR": "BRENT",
    "NG": "NATGAS",
    "USDRUBF": "USDRUB",
    "SI": "USDRUB",
}


def git_clean() -> bool:
    r = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, check=False)
    return r.stdout.strip() == ""


def resolve_underlying(symbol: str) -> str:
    base = str(symbol or "").split("@", 1)[0]

    if base == "BR_ROLLING":
        return "BRENT"

    for prefix, underlying in FUTURES_PREFIX_MAP.items():
        if base.startswith(prefix):
            return underlying

    return base


def classify(row: dict[str, Any], min_trades: int, min_pf: float, min_expectancy: float) -> tuple[str, str]:
    trades = int(row.get("trades") or 0)
    pf = row.get("profit_factor")
    expectancy = float(row.get("expectancy") or 0.0)
    net_pnl = float(row.get("net_pnl") or 0.0)

    if trades < min_trades:
        return "UNDERLYING_INSUFFICIENT_SAMPLE", "trades_below_minimum"

    if pf is not None and float(pf) >= min_pf and expectancy > min_expectancy and net_pnl > 0:
        return "UNDERLYING_EDGE", "positive_edge_across_contracts"

    if net_pnl <= 0 or expectancy <= 0:
        return "UNDERLYING_NO_EDGE", "non_positive_pnl_or_expectancy"

    return "UNDERLYING_OBSERVE", "positive_but_below_threshold"


def score(row: dict[str, Any]) -> float:
    trades = float(row.get("trades") or 0.0)
    pf = float(row.get("profit_factor") or 0.0)
    expectancy = float(row.get("expectancy") or 0.0)
    winrate = float(row.get("winrate") or 0.0)
    contracts = float(row.get("contracts_count") or 0.0)

    sample_score = min(trades / 100.0, 1.0)
    pf_score = min(pf / 2.0, 1.5)
    expectancy_score = max(min(expectancy, 5.0), -5.0) / 5.0
    contract_score = min(contracts / 3.0, 1.0)

    return round(
        0.30 * sample_score
        + 0.25 * pf_score
        + 0.25 * expectancy_score
        + 0.10 * winrate
        + 0.10 * contract_score,
        6,
    )


LOAD_SQL = """
SELECT
    symbol,
    strategy,
    timeframe,
    origin,
    side,
    extract(hour from (entry_ts AT TIME ZONE 'Europe/Moscow'))::int AS hour_msk,
    net_pnl,
    holding_seconds,
    entry_ts,
    exit_ts
FROM analytics_strategy_trades_v2
WHERE strategy <> ''
  AND entry_ts IS NOT NULL
  AND exit_ts IS NOT NULL;
"""


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, str, str, str, int], dict[str, Any]] = {}

    for row in rows:
        underlying = resolve_underlying(row["symbol"])
        key = (
            underlying,
            row["strategy"],
            row["timeframe"],
            row["origin"],
            row["side"],
            int(row["hour_msk"]),
        )

        bucket = buckets.setdefault(
            key,
            {
                "underlying": underlying,
                "strategy": row["strategy"],
                "timeframe": row["timeframe"],
                "origin": row["origin"],
                "side": row["side"],
                "hour_msk": int(row["hour_msk"]),
                "symbols": set(),
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "net_pnl": 0.0,
                "gross_profit": 0.0,
                "gross_loss": 0.0,
                "holding_sum": 0.0,
                "first_entry": row["entry_ts"],
                "last_exit": row["exit_ts"],
            },
        )

        pnl = float(row["net_pnl"] or 0.0)
        bucket["symbols"].add(row["symbol"])
        bucket["trades"] += 1
        bucket["net_pnl"] += pnl
        bucket["holding_sum"] += float(row.get("holding_seconds") or 0.0)

        if pnl > 0:
            bucket["wins"] += 1
            bucket["gross_profit"] += pnl
        else:
            bucket["losses"] += 1
            bucket["gross_loss"] += abs(pnl)

        if row["entry_ts"] < bucket["first_entry"]:
            bucket["first_entry"] = row["entry_ts"]

        if row["exit_ts"] > bucket["last_exit"]:
            bucket["last_exit"] = row["exit_ts"]

    result: list[dict[str, Any]] = []
    for bucket in buckets.values():
        trades = int(bucket["trades"])
        gross_loss = float(bucket["gross_loss"])
        symbols = sorted(bucket["symbols"])

        bucket["contracts_count"] = len(symbols)
        bucket["contracts"] = ",".join(symbols)
        bucket["winrate"] = round(bucket["wins"] / trades, 6) if trades else None
        bucket["expectancy"] = round(bucket["net_pnl"] / trades, 6) if trades else None
        bucket["profit_factor"] = round(bucket["gross_profit"] / gross_loss, 6) if gross_loss > 0 else None
        bucket["avg_holding_seconds"] = round(bucket["holding_sum"] / trades, 2) if trades else None
        bucket["net_pnl"] = round(bucket["net_pnl"], 6)

        del bucket["symbols"]
        del bucket["gross_profit"]
        del bucket["gross_loss"]
        del bucket["holding_sum"]

        result.append(bucket)

    result.sort(key=lambda x: (float(x["net_pnl"]), int(x["trades"])), reverse=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-trades", type=int, default=50)
    parser.add_argument("--min-pf", type=float, default=1.30)
    parser.add_argument("--min-expectancy", type=float, default=0.0)
    args = parser.parse_args()

    print("UNDERLYING_EDGE_ENGINE_V1", flush=True)
    print(
        "UNDERLYING_EDGE_ENGINE_V1_CONFIG "
        f"min_trades={args.min_trades} "
        f"min_pf={args.min_pf} "
        f"min_expectancy={args.min_expectancy} "
        f"git_clean={git_clean()}",
        flush=True,
    )

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(LOAD_SQL)
            rows = [dict(x) for x in cur.fetchall()]

    aggregated = aggregate(rows)
    summary: dict[str, int] = {}

    for row in aggregated:
        verdict, reason = classify(row, args.min_trades, args.min_pf, args.min_expectancy)
        edge_score = score(row)
        summary[verdict] = summary.get(verdict, 0) + 1

        print(
            " ".join(
                ["UNDERLYING_EDGE_ENGINE_V1_ROW"]
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
        print(f"UNDERLYING_EDGE_ENGINE_V1_SUMMARY verdict={verdict} rows={count}", flush=True)

    print("UNDERLYING_EDGE_ENGINE_V1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
