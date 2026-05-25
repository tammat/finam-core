from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg


KEEP_REGIME = "LOW_IMPULSE"
KEEP_TREND = "down"
KEEP_VOLATILITY = "high"


@dataclass(frozen=True)
class Metrics:
    trades: int
    wins: int
    losses: int
    net_pnl: float
    expectancy: float
    profit_factor: float
    winrate: float


def calc_metrics(pnls: list[float]) -> Metrics:
    trades = len(pnls)

    wins = sum(1 for x in pnls if x > 0)
    losses = sum(1 for x in pnls if x <= 0)

    net_pnl = sum(pnls)

    gross_profit = sum(x for x in pnls if x > 0)
    gross_loss = abs(sum(x for x in pnls if x < 0))

    expectancy = net_pnl / trades if trades else 0.0

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else 0.0
    )

    winrate = wins / trades if trades else 0.0

    return Metrics(
        trades=trades,
        wins=wins,
        losses=losses,
        net_pnl=net_pnl,
        expectancy=expectancy,
        profit_factor=profit_factor,
        winrate=winrate,
    )


def duration_bucket(minutes: float) -> str:
    if minutes < 5:
        return "SCALP_LT_5M"

    if minutes < 15:
        return "FAST_5_15M"

    if minutes < 60:
        return "INTRADAY_15_60M"

    if minutes < 240:
        return "SWING_1_4H"

    return "LONG_GT_4H"


def status_for(metrics: Metrics) -> str:
    if metrics.trades < 5:
        return "LOW_SAMPLE"

    if metrics.profit_factor >= 1.20 and metrics.expectancy > 0:
        return "CONFIRMED"

    if metrics.profit_factor >= 1.00 and metrics.expectancy > 0:
        return "WATCH"

    return "FAILED"


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    sql = """
    SELECT
        EXTRACT(EPOCH FROM (
            COALESCE(tcs.exit_ts, now()) - tcs.entry_ts
        )) / 60.0 AS duration_minutes,
        a.pnl
    FROM trade_context_snapshots tcs
    JOIN trade_attribution_v2 a
      ON a.closed_trade_id = tcs.closed_trade_id
    WHERE tcs.symbol = 'BRM6@RTSX'
      AND tcs.strategy = 'BR_CONSERVATIVE_BREAKOUT'
      AND a.strategy = 'BR_CONSERVATIVE_BREAKOUT'
      AND tcs.context_quality = 'FULL'
      AND tcs.regime = %(regime)s
      AND tcs.trend = %(trend)s
      AND tcs.volatility = %(volatility)s
      AND tcs.entry_ts IS NOT NULL
      AND tcs.exit_ts IS NOT NULL
    ORDER BY tcs.entry_ts;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                {
                    "regime": KEEP_REGIME,
                    "trend": KEEP_TREND,
                    "volatility": KEEP_VOLATILITY,
                },
            )

            rows = cur.fetchall()

    grouped: dict[str, list[float]] = {}

    for duration_minutes, pnl in rows:
        bucket = duration_bucket(float(duration_minutes))

        grouped.setdefault(bucket, [])
        grouped[bucket].append(float(pnl))

    print("BR_TRADE_DURATION_DECOMPOSITION_V1")
    print(f"cluster={KEEP_REGIME}/{KEEP_TREND}/{KEEP_VOLATILITY}")
    print(f"total_trades={len(rows)}")

    print(
        "bucket | trades | wins | losses | "
        "winrate | net_pnl | expectancy | pf | status"
    )

    confirmed = 0
    failed = 0

    for bucket, pnls in sorted(
        grouped.items(),
        key=lambda x: len(x[1]),
        reverse=True,
    ):
        metrics = calc_metrics(pnls)

        status = status_for(metrics)

        if status == "CONFIRMED":
            confirmed += 1

        if status == "FAILED":
            failed += 1

        print(
            f"{bucket} | "
            f"{metrics.trades} | "
            f"{metrics.wins} | "
            f"{metrics.losses} | "
            f"{metrics.winrate:.6f} | "
            f"{metrics.net_pnl:.6f} | "
            f"{metrics.expectancy:.6f} | "
            f"{metrics.profit_factor:.6f} | "
            f"{status}"
        )

    print("SUMMARY")
    print(f"confirmed_buckets={confirmed}")
    print(f"failed_buckets={failed}")

    if confirmed > failed:
        verdict = "DURATION_EDGE_PRESENT"
    elif confirmed == failed:
        verdict = "DURATION_EDGE_UNCLEAR"
    else:
        verdict = "DURATION_EDGE_FAILED"

    print(f"verdict={verdict}")

    print(
        "BR_TRADE_DURATION_DECOMPOSITION_V1_OK "
        f"buckets={len(grouped)} "
        f"verdict={verdict}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
