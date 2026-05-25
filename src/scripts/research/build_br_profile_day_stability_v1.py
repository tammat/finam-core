from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import timezone

import psycopg


SYMBOL = "BRM6@RTSX"
SOURCE_STRATEGY = "BR_CONSERVATIVE_BREAKOUT"
PROFILE = "BR_ASIA_SCALP_MEDIUM_MOVE"


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
    return Metrics(trades, wins, losses, net_pnl, gross_profit, gross_loss, expectancy, profit_factor, winrate)


def day_status(m: Metrics) -> str:
    if m.trades < 3:
        return "LOW_SAMPLE"
    if m.profit_factor >= 1.20 and m.expectancy > 0:
        return "POSITIVE"
    if m.profit_factor >= 1.00 and m.expectancy > 0:
        return "WEAK_POSITIVE"
    return "NEGATIVE"


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    sql = """
    WITH fs AS (
        SELECT
            symbol,
            timeframe,
            ts,
            close,
            LAG(close) OVER (
                PARTITION BY symbol, timeframe
                ORDER BY ts
            ) AS prev_close
        FROM feature_snapshots
        WHERE symbol = %(symbol)s
          AND timeframe = 'M5'
    ),
    profile_rows AS (
        SELECT
            tcs.closed_trade_id,
            COALESCE(tcs.exit_ts, tcs.entry_ts) AS trade_ts,
            a.pnl
        FROM trade_context_snapshots tcs
        JOIN trade_attribution_v2 a
          ON a.closed_trade_id = tcs.closed_trade_id
        WHERE tcs.symbol = %(symbol)s
          AND tcs.strategy = %(strategy)s
          AND a.strategy = %(strategy)s
          AND tcs.context_quality = 'FULL'
          AND tcs.regime = 'LOW_IMPULSE'
          AND tcs.trend = 'down'
          AND tcs.volatility = 'high'
          AND EXTRACT(EPOCH FROM (tcs.exit_ts - tcs.entry_ts)) / 60.0 < 5
          AND tcs.entry_ts IS NOT NULL
          AND tcs.exit_ts IS NOT NULL
          AND EXTRACT(HOUR FROM COALESCE(tcs.exit_ts, tcs.entry_ts)) >= 0
          AND EXTRACT(HOUR FROM COALESCE(tcs.exit_ts, tcs.entry_ts)) < 10
    )
    SELECT
        p.closed_trade_id,
        p.trade_ts,
        p.pnl,
        CASE
            WHEN f.prev_close IS NULL OR f.prev_close = 0 THEN 0
            ELSE ABS(f.close - f.prev_close) / f.prev_close * 100.0
        END AS move_pct
    FROM profile_rows p
    JOIN LATERAL (
        SELECT *
        FROM fs
        WHERE fs.ts <= p.trade_ts
          AND fs.prev_close IS NOT NULL
        ORDER BY fs.ts DESC
        LIMIT 1
    ) f ON TRUE
    WHERE
        CASE
            WHEN f.prev_close IS NULL OR f.prev_close = 0 THEN 0
            ELSE ABS(f.close - f.prev_close) / f.prev_close * 100.0
        END > 0.15
      AND
        CASE
            WHEN f.prev_close IS NULL OR f.prev_close = 0 THEN 0
            ELSE ABS(f.close - f.prev_close) / f.prev_close * 100.0
        END <= 0.35
    ORDER BY p.trade_ts ASC, p.closed_trade_id ASC;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"symbol": SYMBOL, "strategy": SOURCE_STRATEGY})
            rows = cur.fetchall()

    by_day: dict[str, list[float]] = defaultdict(list)

    for _, ts, pnl, _ in rows:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        by_day[ts.strftime("%Y-%m-%d")].append(float(pnl or 0.0))

    all_pnls = [float(row[2] or 0.0) for row in rows]
    total = calc_metrics(all_pnls)

    print("BR_PROFILE_DAY_STABILITY_V1")
    print(f"profile={PROFILE}")
    print("definition=LOW_IMPULSE/down/high + ASIA + SCALP_LT_5M + MEDIUM_MOVE")
    print("TOTAL")
    print(
        f"trades={total.trades} wins={total.wins} losses={total.losses} "
        f"winrate={total.winrate:.6f} net_pnl={total.net_pnl:.6f} "
        f"expectancy={total.expectancy:.6f} pf={total.profit_factor:.6f}"
    )

    print("DAY_MAP")
    print("day | trades | wins | losses | winrate | net_pnl | expectancy | pf | status")

    positive_days = 0
    weak_positive_days = 0
    negative_days = 0
    low_sample_days = 0

    day_net_values: list[float] = []

    for day, pnls in sorted(by_day.items()):
        m = calc_metrics(pnls)
        status = day_status(m)
        day_net_values.append(m.net_pnl)

        if status == "POSITIVE":
            positive_days += 1
        elif status == "WEAK_POSITIVE":
            weak_positive_days += 1
        elif status == "NEGATIVE":
            negative_days += 1
        else:
            low_sample_days += 1

        print(
            f"{day} | {m.trades} | {m.wins} | {m.losses} | "
            f"{m.winrate:.6f} | {m.net_pnl:.6f} | {m.expectancy:.6f} | "
            f"{m.profit_factor:.6f} | {status}"
        )

    days = len(by_day)
    positive_like_days = positive_days + weak_positive_days
    effective_days = positive_like_days + negative_days
    positive_day_ratio = positive_like_days / effective_days if effective_days else 0.0

    best_day = max(day_net_values) if day_net_values else 0.0
    worst_day = min(day_net_values) if day_net_values else 0.0
    top_day_contribution = best_day / total.net_pnl if total.net_pnl else 0.0

    if days < 3:
        verdict = "DAY_STABILITY_NOT_CONFIRMED_TOO_FEW_DAYS"
    elif top_day_contribution >= 0.80:
        verdict = "DAY_STABILITY_NOT_CONFIRMED_CONCENTRATED"
    elif positive_day_ratio >= 0.60 and total.profit_factor >= 1.20 and total.expectancy > 0:
        verdict = "DAY_STABILITY_CONFIRMED"
    elif positive_day_ratio >= 0.40 and total.profit_factor >= 1.00:
        verdict = "DAY_STABILITY_WATCH"
    else:
        verdict = "DAY_STABILITY_FAILED"

    print("SUMMARY")
    print(f"days={days}")
    print(f"positive_days={positive_days}")
    print(f"weak_positive_days={weak_positive_days}")
    print(f"negative_days={negative_days}")
    print(f"low_sample_days={low_sample_days}")
    print(f"positive_day_ratio={positive_day_ratio:.6f}")
    print(f"best_day_pnl={best_day:.6f}")
    print(f"worst_day_pnl={worst_day:.6f}")
    print(f"top_day_contribution={top_day_contribution:.6f}")
    print(f"verdict={verdict}")
    print("runtime_enabled=false")
    print(f"BR_PROFILE_DAY_STABILITY_V1_OK verdict={verdict}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
