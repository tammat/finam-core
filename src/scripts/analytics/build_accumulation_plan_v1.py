from __future__ import annotations

import subprocess
from typing import Any

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SQL = """
SELECT
    underlying,
    strategy,
    timeframe,
    source_group,
    side,
    trades,
    confidence_score,
    stability_score,
    validation_verdict,
    validation_reason
FROM (
    SELECT
        split_part(split_part(line, 'underlying=', 2), ' ', 1) AS underlying,
        split_part(split_part(line, 'strategy=', 2), ' ', 1) AS strategy,
        split_part(split_part(line, 'timeframe=', 2), ' ', 1) AS timeframe,
        split_part(split_part(line, 'source_group=', 2), ' ', 1) AS source_group,
        split_part(split_part(line, 'side=', 2), ' ', 1) AS side,
        NULL::int AS trades,
        NULL::float AS confidence_score,
        NULL::float AS stability_score,
        NULL::text AS validation_verdict,
        NULL::text AS validation_reason
    FROM (SELECT ''::text AS line) x
    WHERE false
) q;
"""


EDGE_SQL = """
SELECT
    symbol,
    strategy,
    timeframe,
    origin,
    side,
    COUNT(*) AS trades,
    MIN(entry_ts) AS first_entry,
    MAX(exit_ts) AS last_exit
FROM analytics_strategy_trades_v2
GROUP BY symbol, strategy, timeframe, origin, side

ORDER BY trades DESC;
"""

EQUITY_FILL_SQL = """
SELECT
    symbol,
    'MEAN_REVERSION_EQUITY' AS strategy,
    'LIVE' AS timeframe,
    'paper' AS origin,
    'LONG' AS side,
    GREATEST(COUNT(*) / 2, 0) AS trades,
    MIN(ts) AS first_entry,
    MAX(ts) AS last_exit
FROM fills
WHERE symbol LIKE '%@MISX'
GROUP BY symbol
HAVING COUNT(*) > 0
ORDER BY trades DESC;
"""


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def underlying(symbol: str) -> str:
    base = str(symbol or "").split("@", 1)[0]
    if base.startswith("BR") or base == "BR_ROLLING":
        return "BRENT"
    if base.startswith("NG"):
        return "NATURAL_GAS"
    if base.startswith("USDRUB") or base.startswith("SI"):
        return "USDRUB"
    return base


def required_tracking_rows() -> list[dict[str, Any]]:
    # Русский комментарий: активные root-инструменты должны быть видны в плане накопления
    # даже если paired trades ещё не появились в analytics_strategy_trades_v2.
    return [
        {
            "symbol": "BRN6@RTSX",
            "strategy": "BR_CONSERVATIVE_BREAKOUT",
            "timeframe": "M5",
            "origin": "paper",
            "side": "LONG",
            "trades": 0,
            "first_entry": None,
            "last_exit": None,
        },
        {
            "symbol": "NGN6@RTSX",
            "strategy": "NG_CONSERVATIVE_BREAKOUT_M1",
            "timeframe": "M1",
            "origin": "paper",
            "side": "LONG",
            "trades": 0,
            "first_entry": None,
            "last_exit": None,
        },
        {
            "symbol": "USDRUBF@RTSX",
            "strategy": "USD_INTRADAY_REGIME",
            "timeframe": "M5",
            "origin": "paper",
            "side": "LONG",
            "trades": 0,
            "first_entry": None,
            "last_exit": None,
        },
    ]


def merge_required_tracking_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing = {
        (
            str(r.get("symbol") or ""),
            str(r.get("strategy") or ""),
            str(r.get("timeframe") or ""),
            str(r.get("origin") or ""),
            str(r.get("side") or ""),
        )
        for r in rows
    }

    merged = list(rows)
    for r in required_tracking_rows():
        key = (
            r["symbol"],
            r["strategy"],
            r["timeframe"],
            r["origin"],
            r["side"],
        )
        if key not in existing:
            merged.append(r)

    return merged


def source_group(origin: str) -> str:
    if origin == "paper":
        return "PAPER"
    if origin == "real":
        return "REAL"
    if "replay" in origin:
        return "REPLAY"
    if "historical" in origin:
        return "HISTORICAL_REPLAY"
    return "OTHER"


def plan_action(row: dict[str, Any]) -> tuple[str, str, int, int, int]:
    src = source_group(row["origin"])
    u = underlying(row["symbol"])
    trades = int(row["trades"] or 0)

    target_days = 20
    target_weeks = 4
    target_trades = 100

    if src in {"REPLAY", "HISTORICAL_REPLAY"}:
        return (
            "PAPER_CONFIRMATION_REQUIRED",
            "replay_or_historical_edge_must_be_confirmed_in_paper",
            target_days,
            target_weeks,
            target_trades,
        )

    if src == "PAPER" and trades < 100:
        return (
            "CONTINUE_PAPER_ACCUMULATION",
            "paper_sample_below_minimum_100_trades",
            target_days,
            target_weeks,
            target_trades,
        )

    if src == "PAPER":
        return (
            "READY_FOR_NEXT_VALIDATION",
            "paper_sample_reached_minimum_trade_count",
            target_days,
            target_weeks,
            target_trades,
        )

    return (
        "IGNORE_FOR_EDGE",
        "source_not_allowed_for_edge_validation",
        target_days,
        target_weeks,
        target_trades,
    )


def main() -> int:
    print("ACCUMULATION_PLAN_V1", flush=True)
    print(f"ACCUMULATION_PLAN_V1_CONFIG git_clean={git_clean()}", flush=True)

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(EDGE_SQL)
            rows = [dict(x) for x in cur.fetchall()]

            cur.execute(EQUITY_FILL_SQL)
            rows.extend([dict(x) for x in cur.fetchall()])

            rows = merge_required_tracking_rows(rows)

    summary: dict[str, int] = {}

    for row in rows:
        action, reason, target_days, target_weeks, target_trades = plan_action(row)
        summary[action] = summary.get(action, 0) + 1

        print(
            " ".join(
                [
                    "ACCUMULATION_PLAN_ROW",
                    f"underlying={underlying(row['symbol'])}",
                    f"symbol={row['symbol']}",
                    f"strategy={row['strategy']}",
                    f"timeframe={row['timeframe']}",
                    f"origin={row['origin']}",
                    f"source_group={source_group(row['origin'])}",
                    f"side={row['side']}",
                    f"current_trades={row['trades']}",
                    f"target_trades={target_trades}",
                    f"target_days={target_days}",
                    f"target_weeks={target_weeks}",
                    f"action={action}",
                    f"reason={reason}",
                    f"first_entry={row['first_entry']}",
                    f"last_exit={row['last_exit']}",
                ]
            ),
            flush=True,
        )

    for action, count in sorted(summary.items()):
        print(f"ACCUMULATION_PLAN_SUMMARY action={action} rows={count}", flush=True)

    print("ACCUMULATION_PLAN_V1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
