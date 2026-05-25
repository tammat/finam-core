from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg


KEEP_REGIME = "LOW_IMPULSE"
KEEP_TREND = "down"
KEEP_VOLATILITY = "high"


@dataclass(frozen=True)
class TradeRow:
    ts: datetime
    pnl: float
    hour: int
    session: str


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
        expectancy=expectancy,
        profit_factor=profit_factor,
        winrate=winrate,
    )


def status_for(metrics: Metrics) -> str:
    if metrics.trades < 5:
        return "LOW_SAMPLE"
    if metrics.profit_factor >= 1.20 and metrics.expectancy > 0:
        return "STABLE_POSITIVE"
    if metrics.profit_factor >= 1.00 and metrics.expectancy > 0:
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

    trades: list[TradeRow] = []

    for ts, pnl in rows:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        hour = int(ts.hour)
        trades.append(
            TradeRow(
                ts=ts,
                pnl=float(pnl or 0.0),
                hour=hour,
                session=classify_session(hour),
            )
        )

    by_hour: dict[int, list[float]] = defaultdict(list)
    by_session: dict[str, list[float]] = defaultdict(list)

    for trade in trades:
        by_hour[trade.hour].append(trade.pnl)
        by_session[trade.session].append(trade.pnl)

    print("BR_INTRADAY_TEMPORAL_STABILITY_V1")
    print(f"cluster={KEEP_REGIME}/{KEEP_TREND}/{KEEP_VOLATILITY}")
    print(f"total_trades={len(trades)}")

    print("HOUR_MAP")
    print("hour_utc | session | trades | wins | losses | winrate | net_pnl | expectancy | pf | status")

    positive_hours = 0
    negative_hours = 0
    low_sample_hours = 0

    for hour in sorted(by_hour):
        pnls = by_hour[hour]
        metrics = calc_metrics(pnls)
        session = classify_session(hour)
        status = status_for(metrics)

        if status in {"STABLE_POSITIVE", "WEAK_POSITIVE"}:
            positive_hours += 1
        elif status == "NEGATIVE":
            negative_hours += 1
        else:
            low_sample_hours += 1

        print(
            f"{hour:02d} | "
            f"{session} | "
            f"{metrics.trades} | "
            f"{metrics.wins} | "
            f"{metrics.losses} | "
            f"{metrics.winrate:.6f} | "
            f"{metrics.net_pnl:.6f} | "
            f"{metrics.expectancy:.6f} | "
            f"{metrics.profit_factor:.6f} | "
            f"{status}"
        )

    print("SESSION_MAP")
    print("session | trades | wins | losses | winrate | net_pnl | expectancy | pf | status")

    for session in ("ASIA", "EUROPE", "US_OPEN", "US_LATE"):
        pnls = by_session.get(session, [])
        metrics = calc_metrics(pnls)
        status = status_for(metrics)
        print(
            f"{session} | "
            f"{metrics.trades} | "
            f"{metrics.wins} | "
            f"{metrics.losses} | "
            f"{metrics.winrate:.6f} | "
            f"{metrics.net_pnl:.6f} | "
            f"{metrics.expectancy:.6f} | "
            f"{metrics.profit_factor:.6f} | "
            f"{status}"
        )

    effective_hours = positive_hours + negative_hours
    temporal_stability = positive_hours / effective_hours if effective_hours else 0.0

    us_open_metrics = calc_metrics(by_session.get("US_OPEN", []))
    no_us_open_metrics = calc_metrics(
        [trade.pnl for trade in trades if trade.session != "US_OPEN"]
    )

    print("SUMMARY")
    print(f"positive_hours={positive_hours}")
    print(f"negative_hours={negative_hours}")
    print(f"low_sample_hours={low_sample_hours}")
    print(f"temporal_stability={temporal_stability:.6f}")
    print(f"us_open_pf={us_open_metrics.profit_factor:.6f}")
    print(f"us_open_expectancy={us_open_metrics.expectancy:.6f}")
    print(f"no_us_open_pf={no_us_open_metrics.profit_factor:.6f}")
    print(f"no_us_open_expectancy={no_us_open_metrics.expectancy:.6f}")

    if us_open_metrics.trades >= 5 and us_open_metrics.expectancy < 0:
        us_open_verdict = "US_OPEN_TOXIC"
    else:
        us_open_verdict = "US_OPEN_NOT_CONFIRMED_TOXIC"

    if temporal_stability >= 0.60 and no_us_open_metrics.profit_factor >= 1.20:
        verdict = "TEMPORAL_EDGE_CONFIRMED_EX_US_OPEN"
    elif temporal_stability >= 0.40 and no_us_open_metrics.profit_factor >= 1.00:
        verdict = "TEMPORAL_EDGE_WATCH"
    else:
        verdict = "TEMPORAL_EDGE_UNSTABLE"

    print(f"us_open_verdict={us_open_verdict}")
    print(f"verdict={verdict}")
    print(
        "BR_INTRADAY_TEMPORAL_STABILITY_V1_OK "
        f"hours={len(by_hour)} "
        f"verdict={verdict} "
        f"us_open_verdict={us_open_verdict}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
