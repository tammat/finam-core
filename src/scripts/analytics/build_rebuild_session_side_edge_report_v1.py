from __future__ import annotations

import os
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
        qty,
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

        b.hour_msk AS entry_hour_msk,

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

        b.ts AS entry_ts,
        s.ts AS exit_ts,

        b.price AS entry_price,
        s.price AS exit_price,

        CASE
            WHEN b.side = 'BUY'
                THEN s.price - b.price

            WHEN b.side = 'SELL'
                THEN b.price - s.price

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
    entry_hour_msk,
    entry_side,

    count(*) AS closed_trades,

    round(sum(pnl_points)::numeric, 4) AS pnl_points,

    round(avg(pnl_points)::numeric, 4) AS expectancy_points,

    count(*) FILTER (
        WHERE pnl_points > 0
    ) AS wins,

    count(*) FILTER (
        WHERE pnl_points <= 0
    ) AS losses,

    round(
        (
            count(*) FILTER (
                WHERE pnl_points > 0
            )::numeric
            / NULLIF(count(*), 0)
        ),
        4
    ) AS winrate,

    min(entry_ts) AS first_trade_ts,
    max(exit_ts) AS last_trade_ts

FROM pairs

GROUP BY
    run_id,
    symbol,
    strategy,
    timeframe,
    session_name,
    entry_hour_msk,
    entry_side

ORDER BY
    pnl_points DESC,
    expectancy_points DESC,
    closed_trades DESC;
"""


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout.strip() == ""


def build_status(rows: list[dict]) -> str:
    negative_sell_rows = 0

    for row in rows:
        if (
            row["entry_side"] == "SELL"
            and float(row["expectancy_points"] or 0.0) < 0
        ):
            negative_sell_rows += 1

    if negative_sell_rows > 0:
        return "WARN_NEGATIVE_SELL_EDGE"

    return "OK"


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(
        database_url,
        row_factory=dict_row,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    status = build_status(rows)

    total_closed = sum(
        int(r["closed_trades"])
        for r in rows
    )

    print(
        "REBUILD_SESSION_SIDE_EDGE_REPORT_V1",
        flush=True,
    )

    print(
        "REBUILD_SESSION_SIDE_EDGE_STATUS "
        f"status={status} "
        f"git_clean={git_clean()} "
        f"rows={len(rows)} "
        f"total_closed_trades={total_closed}",
        flush=True,
    )

    for row in rows:
        print(
            "REBUILD_SESSION_SIDE_EDGE_ROW "
            f"run_id={row['run_id']} "
            f"symbol={row['symbol']} "
            f"strategy={row['strategy']} "
            f"timeframe={row['timeframe']} "
            f"session={row['session_name']} "
            f"hour_msk={row['entry_hour_msk']} "
            f"side={row['entry_side']} "
            f"closed_trades={row['closed_trades']} "
            f"pnl_points={row['pnl_points']} "
            f"expectancy_points={row['expectancy_points']} "
            f"wins={row['wins']} "
            f"losses={row['losses']} "
            f"winrate={row['winrate']} "
            f"first_trade_ts={row['first_trade_ts']} "
            f"last_trade_ts={row['last_trade_ts']}",
            flush=True,
        )

    print(
        "REBUILD_SESSION_SIDE_EDGE_REPORT_V1_OK "
        f"status={status} "
        f"rows={len(rows)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
