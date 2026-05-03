# -*- coding: utf-8 -*-
"""
Backtest from PostgreSQL market_data.
Русский комментарий: источник данных только PostgreSQL, SQLite не используется.
"""

from __future__ import annotations

import os
import argparse
from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg2


@dataclass
class Bar:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


def dsn() -> str:
    return os.getenv("DATABASE_URL") or (
        f"postgresql://{os.getenv('DB_USER','finam')}:{os.getenv('DB_PASSWORD','finam')}"
        f"@{os.getenv('DB_HOST','127.0.0.1')}:{os.getenv('DB_PORT','5432')}/{os.getenv('DB_NAME','finam')}"
    )


def parse_ts(value: str | None):
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    ts = datetime.fromisoformat(text)
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def load_bars(symbol: str, timeframe: str, from_ts=None, to_ts=None) -> list[Bar]:
    where = "symbol=%s AND timeframe=%s"
    params = [symbol, timeframe]

    if from_ts:
        where += " AND ts >= %s"
        params.append(from_ts)
    if to_ts:
        where += " AND ts <= %s"
        params.append(to_ts)

    sql = f"""
        SELECT ts, open, high, low, close_price, volume
        FROM market_data
        WHERE {where}
        ORDER BY ts
    """

    with psycopg2.connect(dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()

    return [
        Bar(
            ts=r[0],
            open=float(r[1]),
            high=float(r[2]),
            low=float(r[3]),
            close=float(r[4]),
            volume=float(r[5] or 0.0),
        )
        for r in rows
    ]


def ema(prev: float | None, value: float, period: int) -> float:
    if prev is None:
        return value
    alpha = 2.0 / (period + 1.0)
    return alpha * value + (1.0 - alpha) * prev


def run_backtest(bars: list[Bar], fast: int, slow: int, fee_pct: float) -> dict:
    cash = 0.0
    position = 0
    entry_price = 0.0
    equity_curve = []
    trades = []

    ema_fast = None
    ema_slow = None

    for bar in bars:
        ema_fast = ema(ema_fast, bar.close, fast)
        ema_slow = ema(ema_slow, bar.close, slow)

        if ema_fast is None or ema_slow is None:
            continue

        signal = None
        if ema_fast > ema_slow and position <= 0:
            signal = "BUY"
        elif ema_fast < ema_slow and position >= 0:
            signal = "SELL"

        if signal == "BUY":
            if position < 0:
                pnl = entry_price - bar.close
                fee = abs(entry_price + bar.close) * fee_pct
                cash += pnl - fee
                trades.append(pnl - fee)

            position = 1
            entry_price = bar.close

        elif signal == "SELL":
            if position > 0:
                pnl = bar.close - entry_price
                fee = abs(entry_price + bar.close) * fee_pct
                cash += pnl - fee
                trades.append(pnl - fee)

            position = -1
            entry_price = bar.close

        unrealized = 0.0
        if position > 0:
            unrealized = bar.close - entry_price
        elif position < 0:
            unrealized = entry_price - bar.close

        equity_curve.append(cash + unrealized)

    if not equity_curve:
        return {"trades": 0, "pnl": 0.0, "winrate": 0.0, "max_drawdown": 0.0}

    peak = equity_curve[0]
    max_dd = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        dd = equity - peak
        max_dd = min(max_dd, dd)

    wins = [t for t in trades if t > 0]
    winrate = len(wins) / len(trades) * 100.0 if trades else 0.0

    return {
        "trades": len(trades),
        "pnl": round(cash, 6),
        "winrate": round(winrate, 2),
        "max_drawdown": round(max_dd, 6),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--timeframe", default="M1")
    p.add_argument("--from-ts")
    p.add_argument("--to-ts")
    p.add_argument("--fast", type=int, default=5)
    p.add_argument("--slow", type=int, default=20)
    p.add_argument("--fee-pct", type=float, default=0.0002)
    p.add_argument("--min-bars", type=int, default=30)
    args = p.parse_args()

    bars = load_bars(
        symbol=args.symbol,
        timeframe=args.timeframe,
        from_ts=parse_ts(args.from_ts),
        to_ts=parse_ts(args.to_ts),
    )

    print("BACKTEST_FROM_POSTGRES")
    print(f"symbol={args.symbol}")
    print(f"timeframe={args.timeframe}")
    print(f"bars={len(bars)}")

    if len(bars) < args.min_bars:
        print(f"STATUS=FAIL reason=NOT_ENOUGH_BARS min_bars={args.min_bars}")
        return 1

    result = run_backtest(bars, args.fast, args.slow, args.fee_pct)

    print(f"trades={result['trades']}")
    print(f"pnl={result['pnl']}")
    print(f"winrate={result['winrate']}%")
    print(f"max_drawdown={result['max_drawdown']}")
    print("STATUS=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
