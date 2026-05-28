from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


GATE_CONFIG_PATH = Path("runtime/session_side_execution_gate_v1.json")


SQL = """
WITH ordered AS (
    SELECT
        payload->>'run_id' AS run_id,
        symbol,
        strategy,
        timeframe,
        ts,
        side,
        price,
        EXTRACT(HOUR FROM ts AT TIME ZONE 'Europe/Moscow')::int AS hour_msk,
        row_number() OVER (
            PARTITION BY payload->>'run_id', symbol
            ORDER BY ts
        ) AS rn
    FROM trades
    WHERE
        trade_source = 'paper'
        AND payload->>'historical_replay' = 'true'
        AND strategy = 'HISTORICAL_BREAKOUT_V1'
),
pairs AS (
    SELECT
        b.run_id,
        b.symbol,
        b.strategy,
        b.timeframe,
        b.hour_msk,
        CASE
            WHEN b.hour_msk BETWEEN 0 AND 5 THEN 'азиатская_сессия'
            WHEN b.hour_msk BETWEEN 6 AND 11 THEN 'утро_мск'
            WHEN b.hour_msk BETWEEN 12 AND 15 THEN 'московская_середина'
            WHEN b.hour_msk BETWEEN 16 AND 20 THEN 'вечерняя_сессия'
            ELSE 'ночь'
        END AS session_name,
        b.side AS entry_side,
        b.ts AS entry_ts,
        s.ts AS exit_ts,
        b.price AS entry_price,
        s.price AS exit_price,
        CASE
            WHEN b.side = 'BUY' THEN s.price - b.price
            WHEN b.side = 'SELL' THEN b.price - s.price
            ELSE 0
        END AS pnl_points
    FROM ordered b
    JOIN ordered s
      ON s.run_id = b.run_id
     AND s.symbol = b.symbol
     AND s.rn = b.rn + 1
    WHERE
        b.side IN ('BUY', 'SELL')
        AND s.side IN ('BUY', 'SELL')
)
SELECT
    run_id,
    symbol,
    strategy,
    timeframe,
    session_name,
    hour_msk,
    entry_side,
    count(*) AS closed_trades,
    round(sum(pnl_points)::numeric, 6) AS pnl_points,
    round(avg(pnl_points)::numeric, 6) AS expectancy_points,
    count(*) FILTER (WHERE pnl_points > 0) AS wins,
    count(*) FILTER (WHERE pnl_points <= 0) AS losses
FROM pairs
GROUP BY
    run_id,
    symbol,
    strategy,
    timeframe,
    session_name,
    hour_msk,
    entry_side
ORDER BY symbol, hour_msk, entry_side;
"""


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def load_gate_config() -> dict:
    return json.loads(GATE_CONFIG_PATH.read_text(encoding="utf-8"))


def make_key(row: dict) -> tuple[str, int, str]:
    return (
        str(row["symbol"]),
        int(row["hour_msk"]),
        str(row["entry_side"]).upper(),
    )


def rolling_equivalent_keys(row: dict) -> list[tuple[str, int, str]]:
    symbol = str(row["symbol"])
    hour = int(row["hour_msk"])
    side = str(row["entry_side"]).upper()

    keys = [(symbol, hour, side)]

    if symbol.startswith("BR") and symbol.endswith("@RTSX"):
        keys.append(("BR_ROLLING@RTSX", hour, side))

    return keys


def build_gate_sets(config: dict) -> tuple[set, set, set]:
    allow = {make_key(r) for r in config.get("allow", [])}
    block = {make_key(r) for r in config.get("block", [])}
    insufficient = {make_key(r) for r in config.get("insufficient_data", [])}
    return allow, block, insufficient


def classify(row: dict, allow: set, block: set, insufficient: set) -> str:
    for key in rolling_equivalent_keys(row):
        if key in block:
            return "BLOCK"
    for key in rolling_equivalent_keys(row):
        if key in allow:
            return "ALLOW"
    for key in rolling_equivalent_keys(row):
        if key in insufficient:
            return "INSUFFICIENT_DATA"
    return "NO_MATCH"


def empty_bucket() -> dict:
    return {
        "closed_trades": 0,
        "pnl_points": 0.0,
        "wins": 0,
        "losses": 0,
    }


def add(bucket: dict, row: dict) -> None:
    bucket["closed_trades"] += int(row["closed_trades"] or 0)
    bucket["pnl_points"] += float(row["pnl_points"] or 0.0)
    bucket["wins"] += int(row["wins"] or 0)
    bucket["losses"] += int(row["losses"] or 0)


def expectancy(bucket: dict) -> float:
    trades = int(bucket["closed_trades"] or 0)
    if trades <= 0:
        return 0.0
    return float(bucket["pnl_points"]) / trades


def winrate(bucket: dict) -> float:
    trades = int(bucket["closed_trades"] or 0)
    if trades <= 0:
        return 0.0
    return float(bucket["wins"]) / trades


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    config = load_gate_config()
    allow, block, insufficient = build_gate_sets(config)

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = [dict(r) for r in cur.fetchall()]

    buckets = {
        "ALL": empty_bucket(),
        "ALLOW": empty_bucket(),
        "BLOCK": empty_bucket(),
        "INSUFFICIENT_DATA": empty_bucket(),
        "NO_MATCH": empty_bucket(),
    }

    classified_rows = []

    for row in rows:
        action = classify(row, allow, block, insufficient)
        row["gate_action"] = action
        classified_rows.append(row)

        add(buckets["ALL"], row)
        add(buckets[action], row)

    all_exp = expectancy(buckets["ALL"])
    allow_exp = expectancy(buckets["ALLOW"])
    block_exp = expectancy(buckets["BLOCK"])

    avoided_trades = buckets["BLOCK"]["closed_trades"]
    avoided_pnl = buckets["BLOCK"]["pnl_points"]

    retained_trades = buckets["ALLOW"]["closed_trades"]
    retained_pnl = buckets["ALLOW"]["pnl_points"]

    status = "OK"
    if not git_clean():
        status = "WARN_GIT_DIRTY"
    elif retained_trades <= 0:
        status = "WARN_NO_ALLOWED_TRADES"
    elif avoided_trades <= 0:
        status = "WARN_NO_BLOCKED_TRADES"
    elif allow_exp <= all_exp:
        status = "WARN_GATE_DOES_NOT_IMPROVE_EXPECTANCY"

    print("EDGE_GATE_EFFECTIVENESS_REPORT_V1", flush=True)

    print(
        "EDGE_GATE_EFFECTIVENESS_STATUS",
        f"status={status}",
        f"git_clean={git_clean()}",
        f"windows={len(rows)}",
        f"allow_windows={len(allow)}",
        f"block_windows={len(block)}",
        f"insufficient_windows={len(insufficient)}",
        flush=True,
    )

    for name in ("ALL", "ALLOW", "BLOCK", "INSUFFICIENT_DATA", "NO_MATCH"):
        bucket = buckets[name]
        print(
            "EDGE_GATE_EFFECTIVENESS_BUCKET",
            f"gate_action={name}",
            f"closed_trades={bucket['closed_trades']}",
            f"pnl_points={round(bucket['pnl_points'], 6)}",
            f"expectancy_points={round(expectancy(bucket), 6)}",
            f"wins={bucket['wins']}",
            f"losses={bucket['losses']}",
            f"winrate={round(winrate(bucket), 6)}",
            flush=True,
        )

    print(
        "EDGE_GATE_EFFECTIVENESS_DELTA",
        f"all_expectancy={round(all_exp, 6)}",
        f"allow_expectancy={round(allow_exp, 6)}",
        f"block_expectancy={round(block_exp, 6)}",
        f"expectancy_lift={round(allow_exp - all_exp, 6)}",
        f"avoided_trades={avoided_trades}",
        f"avoided_pnl_points={round(avoided_pnl, 6)}",
        f"retained_trades={retained_trades}",
        f"retained_pnl_points={round(retained_pnl, 6)}",
        flush=True,
    )

    for row in sorted(
        classified_rows,
        key=lambda r: (
            str(r["gate_action"]),
            -float(r["pnl_points"] or 0.0),
        ),
    ):
        print(
            "EDGE_GATE_EFFECTIVENESS_ROW",
            f"gate_action={row['gate_action']}",
            f"symbol={row['symbol']}",
            f"session={row['session_name']}",
            f"hour_msk={row['hour_msk']}",
            f"side={row['entry_side']}",
            f"closed_trades={row['closed_trades']}",
            f"pnl_points={row['pnl_points']}",
            f"expectancy_points={row['expectancy_points']}",
            f"wins={row['wins']}",
            f"losses={row['losses']}",
            flush=True,
        )

    print(
        "EDGE_GATE_EFFECTIVENESS_REPORT_V1_OK",
        f"status={status}",
        f"rows={len(rows)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
