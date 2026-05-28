from __future__ import annotations

import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


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
            WHEN b.hour_msk BETWEEN 0 AND 5
                THEN 'азиатская_сессия'

            WHEN b.hour_msk BETWEEN 6 AND 11
                THEN 'утро_мск'

            WHEN b.hour_msk BETWEEN 12 AND 15
                THEN 'московская_середина'

            WHEN b.hour_msk BETWEEN 16 AND 20
                THEN 'вечерняя_сессия'

            ELSE 'ночь'
        END AS session_name,

        b.side AS entry_side,

        CASE
            WHEN b.side = 'BUY'
                THEN s.price - b.price

            ELSE b.price - s.price
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

aggregated AS (
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

        count(*) FILTER (
            WHERE pnl_points > 0
        ) AS wins,

        count(*) FILTER (
            WHERE pnl_points <= 0
        ) AS losses

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
        WHEN closed_trades < 20
            THEN 'INSUFFICIENT_DATA'

        WHEN expectancy_points > 0
            THEN 'ALLOW'

        ELSE 'BLOCK'
    END AS gate_action

FROM aggregated

ORDER BY
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
    database_url = build_psycopg_url()

    with psycopg.connect(
        database_url,
        row_factory=dict_row,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    allow_rows = [
        r for r in rows
        if r["gate_action"] == "ALLOW"
    ]

    block_rows = [
        r for r in rows
        if r["gate_action"] == "BLOCK"
    ]

    insufficient_rows = [
        r for r in rows
        if r["gate_action"] == "INSUFFICIENT_DATA"
    ]

    status = "OK"

    if block_rows:
        status = "WARN_NEGATIVE_WINDOWS"

    print("SESSION_SIDE_EXECUTION_GATE_V1")

    print(
        "SESSION_SIDE_EXECUTION_GATE_STATUS "
        f"status={status} "
        f"git_clean={git_clean()} "
        f"rows={len(rows)} "
        f"allow_rows={len(allow_rows)} "
        f"block_rows={len(block_rows)} "
        f"insufficient_rows={len(insufficient_rows)}"
    )

    for row in rows:
        print(
            "SESSION_SIDE_EXECUTION_GATE_ROW "
            f"symbol={row['symbol']} "
            f"strategy={row['strategy']} "
            f"timeframe={row['timeframe']} "
            f"session={row['session_name']} "
            f"hour_msk={row['hour_msk']} "
            f"side={row['entry_side']} "
            f"closed_trades={row['closed_trades']} "
            f"pnl_points={row['pnl_points']} "
            f"expectancy_points={row['expectancy_points']} "
            f"wins={row['wins']} "
            f"losses={row['losses']} "
            f"gate_action={row['gate_action']}"
        )

    print(
        "SESSION_SIDE_EXECUTION_GATE_V1_OK "
        f"status={status} "
        f"rows={len(rows)}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
