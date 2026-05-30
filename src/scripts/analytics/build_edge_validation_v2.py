from __future__ import annotations

import argparse
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


def source_group(origin: str) -> str:
    if origin == "paper":
        return "PAPER"
    if origin == "real":
        return "REAL"
    if origin == "real_dry_run":
        return "REAL_DRY_RUN"
    if "historical" in origin:
        return "HISTORICAL_REPLAY"
    if "replay" in origin:
        return "REPLAY"
    return "OTHER"


LOAD_SQL = """
SELECT
    symbol,
    strategy,
    timeframe,
    origin,
    side,
    extract(hour from (entry_ts AT TIME ZONE 'Europe/Moscow'))::int AS hour_msk,
    net_pnl,
    entry_ts,
    exit_ts
FROM analytics_strategy_trades_v2
WHERE strategy <> ''
  AND entry_ts IS NOT NULL
  AND exit_ts IS NOT NULL;
"""


def confidence(row: dict[str, Any]) -> float:
    trades_score = min(float(row["trades"]) / 100.0, 1.0)
    pf_score = min(float(row["profit_factor"] or 0.0) / 1.5, 1.0)
    expectancy_score = min(max(float(row["expectancy"] or 0.0), 0.0) / 1.0, 1.0)
    contracts_score = min(float(row["contracts_count"]) / 2.0, 1.0)
    months_score = min(float(row["months_count"]) / 3.0, 1.0)
    days_score = min(float(row["trading_days_count"]) / 60.0, 1.0)

    return round(
        0.25 * trades_score
        + 0.20 * pf_score
        + 0.15 * expectancy_score
        + 0.15 * contracts_score
        + 0.10 * months_score
        + 0.15 * days_score,
        6,
    )


def classify(row: dict[str, Any]) -> tuple[str, str]:
    trades = int(row["trades"])
    pf = row["profit_factor"]
    expectancy = float(row["expectancy"] or 0.0)
    contracts = int(row["contracts_count"])
    months = int(row["months_count"])
    days = int(row["trading_days_count"])
    conf = float(row["confidence_score"])

    if pf is None or float(pf) < 1.0 or expectancy <= 0:
        return "REJECTED_EDGE", "pf_or_expectancy_not_positive"

    if (
        trades >= 100
        and float(pf) >= 1.30
        and contracts >= 2
        and months >= 3
        and days >= 60
        and conf >= 0.80
    ):
        return "CONFIRMED_EDGE", "multi_contract_multi_month_multi_day_confirmed"

    if (
        trades >= 50
        and float(pf) >= 1.20
        and contracts >= 2
        and months >= 2
        and days >= 20
        and conf >= 0.60
    ):
        return "PROBABLE_EDGE", "positive_edge_with_partial_confirmation"

    reasons = []
    if contracts < 2:
        reasons.append("single_contract_bias")
    if months < 2:
        reasons.append("single_month_bias")
    if days < 20:
        reasons.append("insufficient_distinct_days")
    if trades < 50:
        reasons.append("small_sample")
    if not reasons:
        reasons.append("positive_but_not_confirmed")

    return "OBSERVE", ",".join(reasons)


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, str, str, str, int], dict[str, Any]] = {}

    for row in rows:
        underlying = resolve_underlying(row["symbol"])
        src = source_group(str(row["origin"] or ""))
        key = (
            underlying,
            row["strategy"],
            row["timeframe"],
            src,
            row["side"],
            int(row["hour_msk"]),
        )

        bucket = buckets.setdefault(
            key,
            {
                "underlying": underlying,
                "strategy": row["strategy"],
                "timeframe": row["timeframe"],
                "source_group": src,
                "side": row["side"],
                "hour_msk": int(row["hour_msk"]),
                "symbols": set(),
                "origins": set(),
                "months": set(),
                "trading_days": set(),
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "net_pnl": 0.0,
                "gross_profit": 0.0,
                "gross_loss": 0.0,
                "first_entry": row["entry_ts"],
                "last_exit": row["exit_ts"],
            },
        )

        pnl = float(row["net_pnl"] or 0.0)
        entry_ts = row["entry_ts"]

        bucket["symbols"].add(row["symbol"])
        bucket["origins"].add(row["origin"])
        bucket["months"].add(entry_ts.strftime("%Y-%m"))
        bucket["trading_days"].add(entry_ts.date().isoformat())
        bucket["trades"] += 1
        bucket["net_pnl"] += pnl

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

        bucket["contracts_count"] = len(bucket["symbols"])
        bucket["contracts"] = ",".join(sorted(bucket["symbols"]))
        bucket["origins_count"] = len(bucket["origins"])
        bucket["origins"] = ",".join(sorted(str(x) for x in bucket["origins"]))
        bucket["months_count"] = len(bucket["months"])
        bucket["months"] = ",".join(sorted(bucket["months"]))
        bucket["trading_days_count"] = len(bucket["trading_days"])
        bucket["first_day"] = min(bucket["trading_days"])
        bucket["last_day"] = max(bucket["trading_days"])
        bucket["winrate"] = round(bucket["wins"] / trades, 6) if trades else None
        bucket["expectancy"] = round(bucket["net_pnl"] / trades, 6) if trades else None
        bucket["profit_factor"] = round(bucket["gross_profit"] / gross_loss, 6) if gross_loss > 0 else None
        bucket["net_pnl"] = round(bucket["net_pnl"], 6)

        for k in ["symbols", "months", "trading_days", "gross_profit", "gross_loss"]:
            if k in bucket and not isinstance(bucket[k], str):
                del bucket[k]

        bucket["confidence_score"] = confidence(bucket)
        verdict, reason = classify(bucket)
        bucket["validation_verdict"] = verdict
        bucket["validation_reason"] = reason

        result.append(bucket)

    result.sort(
        key=lambda x: (
            x["validation_verdict"] == "CONFIRMED_EDGE",
            x["validation_verdict"] == "PROBABLE_EDGE",
            x["validation_verdict"] == "OBSERVE",
            float(x["confidence_score"]),
            float(x["net_pnl"]),
        ),
        reverse=True,
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    print("EDGE_VALIDATION_V2", flush=True)
    print(f"EDGE_VALIDATION_V2_CONFIG git_clean={git_clean()}", flush=True)

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(LOAD_SQL)
            rows = [dict(x) for x in cur.fetchall()]

    result = aggregate(rows)
    summary: dict[str, int] = {}

    for row in result[: args.limit]:
        summary[row["validation_verdict"]] = summary.get(row["validation_verdict"], 0) + 1
        print(
            " ".join(["EDGE_VALIDATION_V2_ROW"] + [f"{k}={v}" for k, v in row.items()]),
            flush=True,
        )

    for verdict, count in sorted(summary.items()):
        print(f"EDGE_VALIDATION_V2_SUMMARY verdict={verdict} rows={count}", flush=True)

    print("EDGE_VALIDATION_V2_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
