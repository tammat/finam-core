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
    session: str


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


def classify_session(hour: int) -> str:
    # Русский комментарий: используем ту же грубую сессионную модель, что и contamination report.
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
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        expectancy=expectancy,
        profit_factor=profit_factor,
        winrate=winrate,
    )


def status_for(metrics: Metrics) -> str:
    if metrics.trades < 10:
        return "LOW_SAMPLE"
    if metrics.profit_factor >= 1.20 and metrics.expectancy > 0:
        return "CONFIRMED"
    if metrics.profit_factor >= 1.00 and metrics.expectancy > 0:
        return "WATCH"
    return "FAILED"


def print_scope(name: str, trades: list[TradeRow], baseline_net: float) -> Metrics:
    pnls = [x.pnl for x in trades]
    metrics = calc_metrics(pnls)
    contribution = metrics.net_pnl / baseline_net if baseline_net else 0.0
    print(
        f"{name} | "
        f"{metrics.trades} | "
        f"{metrics.wins} | "
        f"{metrics.losses} | "
        f"{metrics.winrate:.6f} | "
        f"{metrics.net_pnl:.6f} | "
        f"{metrics.gross_profit:.6f} | "
        f"{metrics.gross_loss:.6f} | "
        f"{metrics.expectancy:.6f} | "
        f"{metrics.profit_factor:.6f} | "
        f"{contribution:.6f} | "
        f"{status_for(metrics)}"
    )
    return metrics


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
        session = classify_session(ts.hour)
        trades.append(TradeRow(ts=ts, pnl=float(pnl or 0.0), session=session))

    baseline = calc_metrics([x.pnl for x in trades])
    baseline_net = baseline.net_pnl

    session_groups: dict[str, list[TradeRow]] = defaultdict(list)
    for t in trades:
        session_groups[t.session].append(t)

    print("BR_SESSION_FILTERED_EDGE_V1")
    print(f"cluster={KEEP_REGIME}/{KEEP_TREND}/{KEEP_VOLATILITY}")
    print("scope | trades | wins | losses | winrate | net_pnl | gross_profit | gross_loss | expectancy | pf | contribution_vs_full | status")

    full = print_scope("FULL_CLUSTER", trades, baseline_net)
    no_us = print_scope("NO_US_OPEN", [x for x in trades if x.session != "US_OPEN"], baseline_net)
    asia = print_scope("ASIA_ONLY", session_groups.get("ASIA", []), baseline_net)
    europe = print_scope("EUROPE_ONLY", session_groups.get("EUROPE", []), baseline_net)
    us_open = print_scope("US_OPEN_ONLY", session_groups.get("US_OPEN", []), baseline_net)
    us_late = print_scope("US_LATE_ONLY", session_groups.get("US_LATE", []), baseline_net)

    print("SUMMARY")
    print(f"full_pf={full.profit_factor:.6f}")
    print(f"no_us_open_pf={no_us.profit_factor:.6f}")
    print(f"us_open_pnl={us_open.net_pnl:.6f}")
    print(f"asia_pnl={asia.net_pnl:.6f}")
    print(f"europe_pnl={europe.net_pnl:.6f}")

    if no_us.trades >= 10 and no_us.profit_factor >= 1.20 and no_us.expectancy > 0:
        verdict = "EDGE_SURVIVES_WITHOUT_US_OPEN"
    elif no_us.trades >= 10 and no_us.profit_factor >= 1.00 and no_us.expectancy > 0:
        verdict = "EDGE_WEAK_WITHOUT_US_OPEN"
    else:
        verdict = "EDGE_DOES_NOT_SURVIVE_FILTER"

    print(f"verdict={verdict}")
    print(
        "BR_SESSION_FILTERED_EDGE_V1_OK "
        f"full_trades={full.trades} "
        f"no_us_open_trades={no_us.trades} "
        f"verdict={verdict}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
