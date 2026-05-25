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


def classify_session(hour: int) -> str:
    if 0 <= hour < 10:
        return "ASIA"
    if 10 <= hour < 15:
        return "EUROPE"
    if 15 <= hour < 19:
        return "US_OPEN"
    return "US_LATE"


def calc_pf(pnls: list[float]) -> float:
    gross_profit = sum(x for x in pnls if x > 0)
    gross_loss = abs(sum(x for x in pnls if x < 0))
    if gross_loss == 0:
        return 0.0
    return gross_profit / gross_loss


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
    ORDER BY COALESCE(tcs.exit_ts, tcs.entry_ts);
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {
                "regime": KEEP_REGIME,
                "trend": KEEP_TREND,
                "volatility": KEEP_VOLATILITY,
            })
            rows = cur.fetchall()

    trades: list[TradeRow] = []
    for ts, pnl in rows:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        trades.append(TradeRow(ts=ts, pnl=float(pnl or 0.0)))

    total_net = sum(t.pnl for t in trades)
    session_map: dict[str, list[float]] = defaultdict(list)
    date_map: dict[str, list[float]] = defaultdict(list)

    for t in trades:
        session_map[classify_session(t.ts.hour)].append(t.pnl)
        date_map[t.ts.strftime("%Y-%m-%d")].append(t.pnl)

    print("BR_EVENT_SESSION_CONTAMINATION_V1")
    print(f"cluster={KEEP_REGIME}/{KEEP_TREND}/{KEEP_VOLATILITY}")
    print(f"total_trades={len(trades)}")
    print("session | trades | net_pnl | expectancy | pf | contribution")

    for session, pnls in sorted(session_map.items(), key=lambda x: sum(x[1]), reverse=True):
        net_pnl = sum(pnls)
        expectancy = net_pnl / len(pnls) if pnls else 0.0
        contribution = net_pnl / total_net if total_net else 0.0
        pf = calc_pf(pnls)
        print(f"{session} | {len(pnls)} | {net_pnl:.6f} | {expectancy:.6f} | {pf:.6f} | {contribution:.6f}")

    print("TOP_DATES")
    sorted_dates = sorted(date_map.items(), key=lambda x: sum(x[1]), reverse=True)

    for date_key, pnls in sorted_dates[:10]:
        net_pnl = sum(pnls)
        contribution = net_pnl / total_net if total_net else 0.0
        print(f"{date_key} | trades={len(pnls)} | net_pnl={net_pnl:.6f} | contribution={contribution:.6f}")

    top3_pnl = sum(sum(v) for _, v in sorted_dates[:3])
    top3_ratio = top3_pnl / total_net if total_net else 0.0

    if top3_ratio >= 0.80:
        verdict = "HIGH_CONTAMINATION"
    elif top3_ratio >= 0.50:
        verdict = "MODERATE_CONTAMINATION"
    else:
        verdict = "LOW_CONTAMINATION"

    print("SUMMARY")
    print(f"top3_day_contribution={top3_ratio:.6f}")
    print(f"verdict={verdict}")
    print(f"BR_EVENT_SESSION_CONTAMINATION_V1_OK trades={len(trades)} verdict={verdict}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
