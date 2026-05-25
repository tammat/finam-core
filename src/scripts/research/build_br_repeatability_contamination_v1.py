from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import timezone

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


def classify_session(hour: int) -> str:
    if 0 <= hour < 10:
        return "ASIA"
    if 10 <= hour < 15:
        return "EUROPE"
    if 15 <= hour < 19:
        return "US_OPEN"
    return "US_LATE"


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
    return Metrics(trades, wins, losses, net_pnl, expectancy, profit_factor, winrate)


def status_for(metrics: Metrics) -> str:
    if metrics.trades < 3:
        return "LOW_SAMPLE"
    if metrics.profit_factor >= 1.20 and metrics.expectancy > 0:
        return "POSITIVE"
    if metrics.profit_factor >= 1.00 and metrics.expectancy > 0:
        return "WEAK_POSITIVE"
    return "NEGATIVE"


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    sql = """
    SELECT
        COALESCE(tcs.exit_ts, tcs.entry_ts) AS ts,
        EXTRACT(EPOCH FROM (tcs.exit_ts - tcs.entry_ts)) / 60.0 AS duration_minutes,
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
    ORDER BY COALESCE(tcs.exit_ts, tcs.entry_ts), tcs.closed_trade_id;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"regime": KEEP_REGIME, "trend": KEEP_TREND, "volatility": KEEP_VOLATILITY})
            rows = cur.fetchall()

    day_all: dict[str, list[float]] = defaultdict(list)
    day_core: dict[str, list[float]] = defaultdict(list)

    for ts, duration_minutes, pnl in rows:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        pnl_f = float(pnl or 0.0)
        day = ts.strftime("%Y-%m-%d")
        session = classify_session(int(ts.hour))
        bucket = duration_bucket(float(duration_minutes or 0.0))

        day_all[day].append(pnl_f)

        if session == "ASIA" and bucket == "SCALP_LT_5M":
            day_core[day].append(pnl_f)

    all_pnls = [p for values in day_all.values() for p in values]
    core_pnls = [p for values in day_core.values() for p in values]

    all_metrics = calc_metrics(all_pnls)
    core_metrics = calc_metrics(core_pnls)

    print("BR_REPEATABILITY_CONTAMINATION_V1")
    print(f"cluster={KEEP_REGIME}/{KEEP_TREND}/{KEEP_VOLATILITY}")
    print("scope | trades | wins | losses | winrate | net_pnl | expectancy | pf | status")
    print(
        f"FULL_CLUSTER | {all_metrics.trades} | {all_metrics.wins} | {all_metrics.losses} | "
        f"{all_metrics.winrate:.6f} | {all_metrics.net_pnl:.6f} | "
        f"{all_metrics.expectancy:.6f} | {all_metrics.profit_factor:.6f} | {status_for(all_metrics)}"
    )
    print(
        f"CORE_SCALP_ASIA | {core_metrics.trades} | {core_metrics.wins} | {core_metrics.losses} | "
        f"{core_metrics.winrate:.6f} | {core_metrics.net_pnl:.6f} | "
        f"{core_metrics.expectancy:.6f} | {core_metrics.profit_factor:.6f} | {status_for(core_metrics)}"
    )

    print("DAY_MAP_CORE_SCALP_ASIA")
    print("day | trades | wins | losses | winrate | net_pnl | expectancy | pf | status")

    positive_days = 0
    negative_days = 0
    low_sample_days = 0

    sorted_days = sorted(day_core.items(), key=lambda x: x[0])

    for day, pnls in sorted_days:
        m = calc_metrics(pnls)
        st = status_for(m)

        if st in {"POSITIVE", "WEAK_POSITIVE"}:
            positive_days += 1
        elif st == "NEGATIVE":
            negative_days += 1
        else:
            low_sample_days += 1

        print(
            f"{day} | {m.trades} | {m.wins} | {m.losses} | "
            f"{m.winrate:.6f} | {m.net_pnl:.6f} | {m.expectancy:.6f} | "
            f"{m.profit_factor:.6f} | {st}"
        )

    top_day_pnl = max((sum(v) for v in day_core.values()), default=0.0)
    top_day_ratio = top_day_pnl / core_metrics.net_pnl if core_metrics.net_pnl else 0.0
    effective_days = positive_days + negative_days
    repeatability_ratio = positive_days / effective_days if effective_days else 0.0

    if top_day_ratio >= 0.80:
        contamination = "HIGH_DAY_CONCENTRATION"
    elif top_day_ratio >= 0.50:
        contamination = "MODERATE_DAY_CONCENTRATION"
    else:
        contamination = "LOW_DAY_CONCENTRATION"

    if repeatability_ratio >= 0.60 and contamination != "HIGH_DAY_CONCENTRATION":
        verdict = "REPEATABILITY_CONFIRMED"
    elif repeatability_ratio >= 0.40:
        verdict = "REPEATABILITY_WATCH"
    else:
        verdict = "REPEATABILITY_NOT_CONFIRMED"

    print("SUMMARY")
    print(f"positive_days={positive_days}")
    print(f"negative_days={negative_days}")
    print(f"low_sample_days={low_sample_days}")
    print(f"repeatability_ratio={repeatability_ratio:.6f}")
    print(f"top_day_contribution={top_day_ratio:.6f}")
    print(f"contamination={contamination}")
    print(f"verdict={verdict}")
    print(f"BR_REPEATABILITY_CONTAMINATION_V1_OK days={len(sorted_days)} verdict={verdict}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
