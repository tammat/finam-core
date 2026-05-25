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
    net_pnl: float
    expectancy: float
    gross_profit: float
    gross_loss: float
    profit_factor: float


def calc_metrics(pnls: list[float]) -> Metrics:
    trades = len(pnls)
    net_pnl = sum(pnls)
    gross_profit = sum(x for x in pnls if x > 0)
    gross_loss = abs(sum(x for x in pnls if x < 0))
    expectancy = net_pnl / trades if trades else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss else 0.0

    return Metrics(
        trades=trades,
        net_pnl=net_pnl,
        expectancy=expectancy,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=profit_factor,
    )


def classify_window(m: Metrics) -> str:
    if m.trades < 10:
        return "LOW_SAMPLE"
    if m.profit_factor >= 1.20 and m.expectancy > 0:
        return "POSITIVE"
    if m.profit_factor >= 1.00 and m.expectancy > 0:
        return "WEAK_POSITIVE"
    return "NEGATIVE"


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

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
      AND tcs.regime = %(regime)s
      AND tcs.trend = %(trend)s
      AND tcs.volatility = %(volatility)s
      AND COALESCE(tcs.exit_ts, tcs.entry_ts) IS NOT NULL
    ORDER BY COALESCE(tcs.exit_ts, tcs.entry_ts) ASC, tcs.closed_trade_id ASC;
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

    trades = [{"ts": row[0], "pnl": float(row[1] or 0.0)} for row in rows]
    total = len(trades)

    print("BR_CLUSTER_REGIME_PERSISTENCE_V1")
    print(f"cluster={KEEP_REGIME}/{KEEP_TREND}/{KEEP_VOLATILITY}")
    print(f"total_trades={total}")
    print(f"window_size={WINDOW_SIZE}")
    print("window | range | first_ts | last_ts | trades | net_pnl | expectancy | pf | state")

    states: list[str] = []
    positive_streak = 0
    max_positive_streak = 0
    current_positive_streak = 0
    decay_after_positive = False
    first_positive_window = 0
    last_positive_window = 0

    window_id = 1

    for start in range(0, total, WINDOW_SIZE):
        end = min(start + WINDOW_SIZE, total)
        chunk = trades[start:end]
        pnls = [x["pnl"] for x in chunk]

        metrics = calc_metrics(pnls)
        state = classify_window(metrics)
        states.append(state)

        is_positive = state in {"POSITIVE", "WEAK_POSITIVE"}

        if is_positive:
            if first_positive_window == 0:
                first_positive_window = window_id
            last_positive_window = window_id
            current_positive_streak += 1
            max_positive_streak = max(max_positive_streak, current_positive_streak)
        else:
            if current_positive_streak > 0 and state == "NEGATIVE":
                decay_after_positive = True
            current_positive_streak = 0

        print(
            f"{window_id} | "
            f"{start + 1}-{end} | "
            f"{chunk[0]['ts']} | "
            f"{chunk[-1]['ts']} | "
            f"{metrics.trades} | "
            f"{metrics.net_pnl:.6f} | "
            f"{metrics.expectancy:.6f} | "
            f"{metrics.profit_factor:.6f} | "
            f"{state}"
        )

        window_id += 1

    positive_windows = sum(1 for s in states if s in {"POSITIVE", "WEAK_POSITIVE"})
    negative_windows = sum(1 for s in states if s == "NEGATIVE")
    low_sample_windows = sum(1 for s in states if s == "LOW_SAMPLE")

    effective_windows = positive_windows + negative_windows
    persistence_ratio = positive_windows / effective_windows if effective_windows else 0.0

    if positive_windows == 0:
        verdict = "NO_PERSISTENCE"
    elif decay_after_positive:
        verdict = "PERSISTENCE_WITH_DECAY"
    elif max_positive_streak >= 2 and persistence_ratio >= 0.60:
        verdict = "PERSISTENCE_CONFIRMED"
    elif max_positive_streak >= 2:
        verdict = "PERSISTENCE_WATCH"
    else:
        verdict = "PERSISTENCE_WEAK"

    print("SUMMARY")
    print(f"positive_windows={positive_windows}")
    print(f"negative_windows={negative_windows}")
    print(f"low_sample_windows={low_sample_windows}")
    print(f"persistence_ratio={persistence_ratio:.6f}")
    print(f"max_positive_streak={max_positive_streak}")
    print(f"first_positive_window={first_positive_window}")
    print(f"last_positive_window={last_positive_window}")
    print(f"decay_after_positive={str(decay_after_positive).lower()}")
    print(f"verdict={verdict}")
    print(
        "BR_CLUSTER_REGIME_PERSISTENCE_V1_OK "
        f"windows={len(states)} "
        f"verdict={verdict}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
