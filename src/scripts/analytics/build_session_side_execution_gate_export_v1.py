from __future__ import annotations

import json
import subprocess
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


EXPORT_PATH = Path("runtime/session_side_execution_gate_v1.json")


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
        b.symbol,
        b.strategy,
        b.timeframe,
        b.hour_msk,
        b.side AS entry_side,
        CASE
            WHEN b.hour_msk BETWEEN 0 AND 5 THEN 'азиатская_сессия'
            WHEN b.hour_msk BETWEEN 6 AND 11 THEN 'утро_мск'
            WHEN b.hour_msk BETWEEN 12 AND 15 THEN 'московская_середина'
            WHEN b.hour_msk BETWEEN 16 AND 20 THEN 'вечерняя_сессия'
            ELSE 'ночь'
        END AS session_name,
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
),
stats AS (
    SELECT
        symbol,
        strategy,
        timeframe,
        session_name,
        hour_msk,
        entry_side,
        count(*) AS closed_trades,
        round(sum(pnl_points)::numeric, 4) AS pnl_points,
        round(avg(pnl_points)::numeric, 4) AS expectancy_points,
        count(*) FILTER (WHERE pnl_points > 0) AS wins,
        count(*) FILTER (WHERE pnl_points <= 0) AS losses
    FROM pairs
    GROUP BY
        symbol,
        strategy,
        timeframe,
        session_name,
        hour_msk,
        entry_side
)
SELECT
    *,
    CASE
        WHEN closed_trades < 20 THEN 'INSUFFICIENT_DATA'
        WHEN expectancy_points > 0 THEN 'ALLOW'
        ELSE 'BLOCK'
    END AS gate_action
FROM stats
ORDER BY
    gate_action,
    expectancy_points DESC,
    closed_trades DESC;
"""


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def main() -> int:
    print("SESSION_SIDE_EXECUTION_GATE_EXPORT_V1", flush=True)

    database_url = build_psycopg_url()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = [dict(r) for r in cur.fetchall()]

    allow_rows = []
    block_rows = []
    insufficient_rows = []

    for row in rows:
        item = {
            "symbol": row["symbol"],
            "strategy": row["strategy"],
            "timeframe": row["timeframe"],
            "session_name": row["session_name"],
            "hour_msk": int(row["hour_msk"]),
            "entry_side": row["entry_side"],
            "closed_trades": int(row["closed_trades"]),
            "pnl_points": float(row["pnl_points"]),
            "expectancy_points": float(row["expectancy_points"]),
            "wins": int(row["wins"]),
            "losses": int(row["losses"]),
            "gate_action": row["gate_action"],
        }

        if row["gate_action"] == "ALLOW":
            allow_rows.append(item)
        elif row["gate_action"] == "BLOCK":
            block_rows.append(item)
        else:
            insufficient_rows.append(item)

    export_data = {
        "version": "session_side_execution_gate_v1",
        "source": "historical_replay",
        "strategy": "HISTORICAL_BREAKOUT_V1",
        "min_closed_trades": 20,
        "git_clean": git_clean(),
        "allow": allow_rows,
        "block": block_rows,
        "insufficient_data": insufficient_rows,
    }

    EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPORT_PATH.write_text(
        json.dumps(export_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        "SESSION_SIDE_EXECUTION_GATE_EXPORT_STATUS",
        f"git_clean={export_data['git_clean']}",
        f"allow_rows={len(allow_rows)}",
        f"block_rows={len(block_rows)}",
        f"insufficient_rows={len(insufficient_rows)}",
        f"path={EXPORT_PATH}",
        flush=True,
    )

    print(
        "SESSION_SIDE_EXECUTION_GATE_EXPORT_V1_OK",
        f"path={EXPORT_PATH}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
