from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg


SYMBOL = "BRM6@RTSX"
STRATEGY = "BR_CONSERVATIVE_BREAKOUT"
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


def bucket_for_gap_ratio(value: float) -> str:
    if value <= 0.10:
        return "NO_OR_TINY_GAP"
    if value <= 0.50:
        return "SMALL_GAP"
    if value <= 1.00:
        return "MEDIUM_GAP"
    if value <= 2.00:
        return "LARGE_GAP"
    return "EXTREME_GAP"


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
    WITH fs AS (
        SELECT
            symbol,
            timeframe,
            ts,
            close,
            atr_proxy,
            LAG(close) OVER (
                PARTITION BY symbol, timeframe
                ORDER BY ts
            ) AS prev_close
        FROM feature_snapshots
        WHERE symbol = %(symbol)s
          AND timeframe = 'M5'
    ),
    trades AS (
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
          AND tcs.regime = %(regime)s
          AND tcs.trend = %(trend)s
          AND tcs.volatility = %(volatility)s
          AND COALESCE(tcs.exit_ts, tcs.entry_ts) IS NOT NULL
    )
    SELECT
        tr.closed_trade_id,
        tr.trade_ts,
        tr.pnl,
        f.close,
        f.prev_close,
        f.atr_proxy,
        CASE
            WHEN f.prev_close IS NULL OR f.prev_close = 0 THEN 0
            ELSE ABS(f.close - f.prev_close) / f.prev_close * 100.0
        END AS gap_percent_proxy,
        CASE
            WHEN f.atr_proxy IS NULL OR f.atr_proxy = 0 THEN 0
            ELSE ABS(f.close - f.prev_close) / f.atr_proxy
        END AS gap_atr_ratio_proxy
    FROM trades tr
    JOIN LATERAL (
        SELECT *
        FROM fs
        WHERE fs.ts <= tr.trade_ts
          AND fs.prev_close IS NOT NULL
        ORDER BY fs.ts DESC
        LIMIT 1
    ) f ON TRUE
    ORDER BY tr.trade_ts ASC, tr.closed_trade_id ASC;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                {
                    "symbol": SYMBOL,
                    "strategy": STRATEGY,
                    "regime": KEEP_REGIME,
                    "trend": KEEP_TREND,
                    "volatility": KEEP_VOLATILITY,
                },
            )
            rows = cur.fetchall()

    grouped: dict[str, list[float]] = {}
    ratios: dict[str, list[float]] = {}

    for row in rows:
        pnl = float(row[2] or 0.0)
        gap_ratio = float(row[7] or 0.0)
        bucket = bucket_for_gap_ratio(gap_ratio)
        grouped.setdefault(bucket, []).append(pnl)
        ratios.setdefault(bucket, []).append(gap_ratio)

    print("BR_GAP_TOXICITY_V1")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print(f"cluster={KEEP_REGIME}/{KEEP_TREND}/{KEEP_VOLATILITY}")
    print("note=gap_proxy_uses_feature_snapshots_close_to_prev_close_until_true_open_available")
    print("bucket | trades | wins | losses | winrate | net_pnl | expectancy | pf | avg_gap_atr_ratio | max_gap_atr_ratio | status")

    toxic_buckets = 0
    confirmed_buckets = 0

    for bucket, pnls in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
        metrics = calc_metrics(pnls)
        status = status_for(metrics)
        avg_ratio = sum(ratios[bucket]) / len(ratios[bucket]) if ratios[bucket] else 0.0
        max_ratio = max(ratios[bucket]) if ratios[bucket] else 0.0

        if status == "FAILED":
            toxic_buckets += 1
        if status == "CONFIRMED":
            confirmed_buckets += 1

        print(
            f"{bucket} | "
            f"{metrics.trades} | "
            f"{metrics.wins} | "
            f"{metrics.losses} | "
            f"{metrics.winrate:.6f} | "
            f"{metrics.net_pnl:.6f} | "
            f"{metrics.expectancy:.6f} | "
            f"{metrics.profit_factor:.6f} | "
            f"{avg_ratio:.6f} | "
            f"{max_ratio:.6f} | "
            f"{status}"
        )

    if toxic_buckets > 0 and confirmed_buckets > 0:
        verdict = "GAP_MIXED_TOXICITY"
    elif toxic_buckets > 0:
        verdict = "GAP_TOXICITY_DETECTED"
    elif confirmed_buckets > 0:
        verdict = "GAP_EDGE_SURVIVES"
    else:
        verdict = "GAP_EDGE_UNCLEAR"

    print("SUMMARY")
    print(f"total_trades={len(rows)}")
    print(f"buckets={len(grouped)}")
    print(f"toxic_buckets={toxic_buckets}")
    print(f"confirmed_buckets={confirmed_buckets}")
    print(f"verdict={verdict}")
    print(f"BR_GAP_TOXICITY_V1_OK trades={len(rows)} verdict={verdict}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
