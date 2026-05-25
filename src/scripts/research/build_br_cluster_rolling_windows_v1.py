from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg


KEEP_REGIME = "LOW_IMPULSE"
KEEP_TREND = "down"
KEEP_VOLATILITY = "high"

WINDOW_SIZE = 20


@dataclass(frozen=True)
class Metrics:
    trades: int
    wins: int
    losses: int
    net_pnl: float
    expectancy: float
    gross_profit: float
    gross_loss: float
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
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=profit_factor,
        winrate=winrate,
    )


def status_for(metrics: Metrics) -> str:
    if metrics.trades < 10:
        return "LOW_SAMPLE"

    if metrics.profit_factor >= 1.20 and metrics.expectancy > 0:
        return "STRONG"

    if metrics.profit_factor >= 1.00 and metrics.expectancy > 0:
        return "WEAK_POSITIVE"

    return "NEGATIVE"


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    sql = """
    SELECT
        tcs.entry_ts,
        a.pnl
    FROM trade_context_snapshots tcs
    JOIN trade_attribution_v2 a
      ON a.closed_trade_id = tcs.closed_trade_id
    WHERE tcs.symbol = 'BRM6@RTSX'
      AND tcs.strategy = 'BR_CONSERVATIVE_BREAKOUT'
      AND tcs.context_quality = 'FULL'
      AND tcs.regime = %(regime)s
      AND tcs.trend = %(trend)s
      AND tcs.volatility = %(volatility)s
    ORDER BY tcs.entry_ts ASC;
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

    trades = [
        {
            "ts": row[0],
            "pnl": float(row[1]),
        }
        for row in rows
    ]

    total = len(trades)

    print("BR_CLUSTER_ROLLING_WINDOWS_V1")
    print(
        f"cluster={KEEP_REGIME}/{KEEP_TREND}/{KEEP_VOLATILITY}"
    )
    print(f"total_trades={total}")
    print(f"window_size={WINDOW_SIZE}")

    print(
        "window | "
        "range | "
        "trades | "
        "wins | "
        "losses | "
        "winrate | "
        "net_pnl | "
        "expectancy | "
        "pf | "
        "status"
    )

    strong_windows = 0
    negative_windows = 0

    window_id = 1

    for start in range(0, total, WINDOW_SIZE):
        end = min(start + WINDOW_SIZE, total)

        chunk = trades[start:end]

        pnls = [x["pnl"] for x in chunk]

        metrics = calc_metrics(pnls)

        status = status_for(metrics)

        if status == "STRONG":
            strong_windows += 1

        if status == "NEGATIVE":
            negative_windows += 1

        print(
            f"{window_id} | "
            f"{start + 1}-{end} | "
            f"{metrics.trades} | "
            f"{metrics.wins} | "
            f"{metrics.losses} | "
            f"{metrics.winrate:.6f} | "
            f"{metrics.net_pnl:.6f} | "
            f"{metrics.expectancy:.6f} | "
            f"{metrics.profit_factor:.6f} | "
            f"{status}"
        )

        window_id += 1

    stability_ratio = (
        strong_windows / (strong_windows + negative_windows)
        if (strong_windows + negative_windows) > 0
        else 0.0
    )

    print("SUMMARY")
    print(f"strong_windows={strong_windows}")
    print(f"negative_windows={negative_windows}")
    print(f"stability_ratio={stability_ratio:.6f}")

    if stability_ratio >= 0.70:
        verdict = "REGIME_EDGE_STABLE"
    elif stability_ratio >= 0.40:
        verdict = "REGIME_EDGE_TRANSITION"
    else:
        verdict = "REGIME_EDGE_UNSTABLE"

    print(f"verdict={verdict}")

    print(
        "BR_CLUSTER_ROLLING_WINDOWS_V1_OK "
        f"windows={window_id - 1} "
        f"verdict={verdict}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
