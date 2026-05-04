# -*- coding: utf-8 -*-
"""
Backtest from PostgreSQL market_data.
Русский комментарий: источник данных только PostgreSQL, SQLite не используется.
"""

from __future__ import annotations

import os
import argparse
from dataclasses import dataclass
from collections import deque
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

def ema_series(values: list[float], period: int) -> list[float]:
    """Русский комментарий: EMA по списку значений для построения regime filter."""
    k = 2 / (period + 1)
    result: list[float] = []
    prev = None

    for v in values:
        if prev is None:
            prev = v
        else:
            prev = v * k + prev * (1 - k)
        result.append(prev)

    return result


def build_regime_map(regime_bars: list[Bar], fast_period: int, slow_period: int) -> list[tuple[datetime, int]]:
    """Русский комментарий: строит карту режима по старшему ТФ: 1=up, -1=down, 0=neutral."""
    if not regime_bars:
        return []
    if fast_period < 2 or slow_period < 2:
        raise ValueError("regime EMA periods must be >= 2")

    closes = [b.close for b in regime_bars]
    fast = ema_series(closes, fast_period)
    slow = ema_series(closes, slow_period)

    result: list[tuple[datetime, int]] = []
    warmup = max(fast_period, slow_period)

    for i, bar in enumerate(regime_bars):
        if i < warmup:
            continue
        direction = 0
        if fast[i] > slow[i]:
            direction = 1
        elif fast[i] < slow[i]:
            direction = -1
        result.append((bar.ts, direction))

    return result


def regime_direction_at(regime_map: list[tuple[datetime, int]], ts: datetime, start_idx: int) -> tuple[int, int]:
    """Русский комментарий: возвращает последний известный режим M15 на момент M5-бара."""
    if not regime_map:
        return 0, start_idx

    idx = start_idx
    while idx + 1 < len(regime_map) and regime_map[idx + 1][0] <= ts:
        idx += 1

    if regime_map[idx][0] <= ts:
        return regime_map[idx][1], idx
    return 0, idx

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



def true_range(bar: Bar, prev_close: float | None) -> float:
    """Русский комментарий: расчет true range для ATR в breakout-backtest."""
    if prev_close is None:
        return bar.high - bar.low
    return max(
        bar.high - bar.low,
        abs(bar.high - prev_close),
        abs(bar.low - prev_close),
    )


def run_breakout_backtest(
    bars: list[Bar],
    window: int,
    atr_period: int,
    stop_atr: float,
    take_atr: float,
    fee_pct: float,
    regime_map: list[tuple[datetime, int]] | None = None,
) -> dict:
    """Русский комментарий: breakout по пробою диапазона последних N баров."""
    position = 0
    entry_price = 0.0
    stop_price = 0.0
    take_price = 0.0
    cash = 0.0
    trades: list[float] = []
    equity_curve: list[float] = []

    highs: deque[float] = deque(maxlen=window)
    lows: deque[float] = deque(maxlen=window)
    tr_values: deque[float] = deque(maxlen=atr_period)
    prev_close: float | None = None
    regime_map = regime_map or []
    regime_idx = 0

    for bar in bars:
        tr_values.append(true_range(bar, prev_close))
        prev_close = bar.close

        if len(highs) >= window and len(lows) >= window and len(tr_values) >= atr_period:
            range_high = max(highs)
            range_low = min(lows)
            atr = sum(tr_values) / len(tr_values)

            regime_direction = 0
            if regime_map:
                regime_direction, regime_idx = regime_direction_at(regime_map, bar.ts, regime_idx)

            if position == 0:
                if bar.close > range_high and (not regime_map or regime_direction == 1):
                    position = 1
                    entry_price = bar.close
                    stop_price = entry_price - atr * stop_atr
                    take_price = entry_price + atr * take_atr
                elif bar.close < range_low and (not regime_map or regime_direction == -1):
                    position = -1
                    entry_price = bar.close
                    stop_price = entry_price + atr * stop_atr
                    take_price = entry_price - atr * take_atr

            elif position > 0:
                exit_price = None
                if bar.low <= stop_price:
                    exit_price = stop_price
                elif bar.high >= take_price:
                    exit_price = take_price
                elif bar.close < range_low:
                    exit_price = bar.close

                if exit_price is not None:
                    pnl = exit_price - entry_price
                    fee = abs(entry_price + exit_price) * fee_pct
                    result = pnl - fee
                    cash += result
                    trades.append(result)
                    position = 0

            elif position < 0:
                exit_price = None
                if bar.high >= stop_price:
                    exit_price = stop_price
                elif bar.low <= take_price:
                    exit_price = take_price
                elif bar.close > range_high:
                    exit_price = bar.close

                if exit_price is not None:
                    pnl = entry_price - exit_price
                    fee = abs(entry_price + exit_price) * fee_pct
                    result = pnl - fee
                    cash += result
                    trades.append(result)
                    position = 0

        unrealized = 0.0
        if position > 0:
            unrealized = bar.close - entry_price
        elif position < 0:
            unrealized = entry_price - bar.close
        equity_curve.append(cash + unrealized)

        highs.append(bar.high)
        lows.append(bar.low)

    if position != 0 and bars:
        last = bars[-1].close
        pnl = (last - entry_price) if position > 0 else (entry_price - last)
        fee = abs(entry_price + last) * fee_pct
        result = pnl - fee
        cash += result
        trades.append(result)
        equity_curve.append(cash)

    if not equity_curve:
        return {"trades": 0, "pnl": 0.0, "winrate": 0.0, "max_drawdown": 0.0}

    peak = equity_curve[0]
    max_dd = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)

    wins = [t for t in trades if t > 0]
    winrate = len(wins) / len(trades) * 100.0 if trades else 0.0

    return {
        "trades": len(trades),
        "pnl": round(cash, 6),
        "winrate": round(winrate, 2),
        "max_drawdown": round(max_dd, 6),
    }


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
    p.add_argument("--mode", choices=("ema", "breakout"), default="ema")
    p.add_argument("--fast", type=int, default=5)
    p.add_argument("--slow", type=int, default=20)
    p.add_argument("--fee-pct", type=float, default=0.0002)
    p.add_argument("--breakout-window", type=int, default=20)
    p.add_argument("--atr-period", type=int, default=14)
    p.add_argument("--stop-atr", type=float, default=1.5)
    p.add_argument("--take-atr", type=float, default=2.0)
    p.add_argument("--min-bars", type=int, default=30)
    p.add_argument("--regime-timeframe", default=None)
    p.add_argument("--regime-fast", type=int, default=5)
    p.add_argument("--regime-slow", type=int, default=20)
    args = p.parse_args()

    bars = load_bars(
        symbol=args.symbol,
        timeframe=args.timeframe,
        from_ts=parse_ts(args.from_ts),
        to_ts=parse_ts(args.to_ts),
    )

    regime_map: list[tuple[datetime, int]] = []
    if args.regime_timeframe:
        regime_bars = load_bars(
            symbol=args.symbol,
            timeframe=args.regime_timeframe,
            from_ts=parse_ts(args.from_ts),
            to_ts=parse_ts(args.to_ts),
        )
        regime_map = build_regime_map(
            regime_bars=regime_bars,
            fast_period=args.regime_fast,
            slow_period=args.regime_slow,
        )

    print("BACKTEST_FROM_POSTGRES")
    print(f"symbol={args.symbol}")
    print(f"timeframe={args.timeframe}")
    print(f"bars={len(bars)}")
    print(f"mode={args.mode}")
    if args.regime_timeframe:
        print(f"regime_timeframe={args.regime_timeframe}")
        print(f"regime_fast={args.regime_fast}")
        print(f"regime_slow={args.regime_slow}")
        print(f"regime_points={len(regime_map)}")

    if len(bars) < args.min_bars:
        print(f"STATUS=FAIL reason=NOT_ENOUGH_BARS min_bars={args.min_bars}")
        return 1

    if args.mode == "ema":
        result = run_backtest(bars, args.fast, args.slow, args.fee_pct)
    else:
        result = run_breakout_backtest(
            bars=bars,
            window=args.breakout_window,
            atr_period=args.atr_period,
            stop_atr=args.stop_atr,
            take_atr=args.take_atr,
            fee_pct=args.fee_pct,
            regime_map=regime_map,
        )

    print(f"trades={result['trades']}")
    print(f"pnl={result['pnl']}")
    print(f"winrate={result['winrate']}%")
    print(f"max_drawdown={result['max_drawdown']}")
    print("STATUS=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
