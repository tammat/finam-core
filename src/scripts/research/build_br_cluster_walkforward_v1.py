from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime

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
    gross_profit: float
    gross_loss: float
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
    profit_factor = gross_profit / gross_loss if gross_loss else 0.0
    winrate = wins / trades if trades else 0.0

    return Metrics(
        trades=trades,
        wins=wins,
        losses=losses,
        net_pnl=net_pnl,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        expectancy=expectancy,
        profit_factor=profit_factor,
        winrate=winrate,
    )


def status_for(metrics: Metrics, *, min_trades: int) -> str:
    if metrics.trades < min_trades:
        return "LOW_SAMPLE"
    if metrics.profit_factor >= 1.10 and metrics.expectancy > 0:
        return "CONFIRMED"
    if metrics.profit_factor >= 1.00 and metrics.expectancy > 0:
        return "WATCH"
    return "FAILED"


def main() -> int:
    database_url = os.environ["DATABASE_URL"]
    min_trades = int(os.getenv("BR_CLUSTER_WF_MIN_TRADES", "20"))

    sql = """
    SELECT
        COALESCE(tcs.exit_ts, tcs.entry_ts) AS ts,
        a.pnl
    FROM trade_context_snapshots tcs
    JOIN trade_attribution_v2 a
      ON a.closed_trade_id = tcs.closed_trade_id
    WHERE tcs.symbol = 'BRM6@RTSX'
      AND tcs.strategy = 'BR_CONSERVATIVE_BREAKOUT'
      AND a.strategy = 'BR_CONSERVATIVE_BREAKOUT'
      AND tcs.context_quality = 'FULL'
      AND tcs.regime = %s
      AND tcs.trend = %s
      AND tcs.volatility = %s
      AND COALESCE(tcs.exit_ts, tcs.entry_ts) IS NOT NULL
    ORDER BY COALESCE(tcs.exit_ts, tcs.entry_ts) ASC, tcs.closed_trade_id ASC
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (KEEP_REGIME, KEEP_TREND, KEEP_VOLATILITY))
            rows = cur.fetchall()

    pnls = [float(row[1] or 0.0) for row in rows]
    timestamps = [row[0] for row in rows]

    total = len(pnls)
    if total == 0:
        print("BR_CLUSTER_WALKFORWARD_V1")
        print("cluster=LOW_IMPULSE/down/high")
        print("BR_CLUSTER_WALKFORWARD_V1_OK total=0 status=NO_DATA")
        return 0

    split = int(total * 0.7)
    if split <= 0:
        split = total

    train_pnls = pnls[:split]
    test_pnls = pnls[split:]

    train = calc_metrics(train_pnls)
    test = calc_metrics(test_pnls)
    all_metrics = calc_metrics(pnls)

    train_status = status_for(train, min_trades=min_trades)
    test_status = status_for(test, min_trades=max(5, min_trades // 2))

    stability = 0.0
    if train.profit_factor > 0:
        stability = min(test.profit_factor / train.profit_factor, train.profit_factor / test.profit_factor) if test.profit_factor > 0 else 0.0

    if train_status == "CONFIRMED" and test_status in {"CONFIRMED", "WATCH"} and stability >= 0.50:
        verdict = "CLUSTER_OOS_CONFIRMED"
    elif test.trades < max(5, min_trades // 2):
        verdict = "CLUSTER_LOW_OOS_SAMPLE"
    elif test.profit_factor >= 1.0 and test.expectancy > 0:
        verdict = "CLUSTER_OOS_WATCH"
    else:
        verdict = "CLUSTER_OOS_FAILED"

    print("BR_CLUSTER_WALKFORWARD_V1")
    print("cluster=LOW_IMPULSE/down/high")
    print(f"total_trades={total}")
    print(f"first_ts={timestamps[0]}")
    print(f"last_ts={timestamps[-1]}")
    print("scope | trades | wins | losses | winrate | net_pnl | expectancy | pf | status")

    for name, metrics, status in (
        ("ALL", all_metrics, status_for(all_metrics, min_trades=min_trades)),
        ("TRAIN_70", train, train_status),
        ("TEST_30", test, test_status),
    ):
        print(
            f"{name} | "
            f"{metrics.trades} | "
            f"{metrics.wins} | "
            f"{metrics.losses} | "
            f"{metrics.winrate:.6f} | "
            f"{metrics.net_pnl:.6f} | "
            f"{metrics.expectancy:.6f} | "
            f"{metrics.profit_factor:.6f} | "
            f"{status}"
        )

    print("IMPACT")
    print(f"stability={stability:.6f}")
    print(f"verdict={verdict}")
    print(
        "BR_CLUSTER_WALKFORWARD_V1_OK "
        f"total={total} "
        f"train={train.trades} "
        f"test={test.trades} "
        f"verdict={verdict}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
