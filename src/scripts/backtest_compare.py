# -*- coding: utf-8 -*-
"""
Backtest compare (SQLite bars) for NGH6@RTSX (or any symbol).

Источники:
- SQLite: table bars(symbol, timeframe, ts, open, high, low, close, volume)

Что сравниваем (3 стратегии):
A) Session VWAP Bands (mean reversion): VWAP + k*std(residual) внутри UTC-дня
B) Anchored VWAP Bands (mean reversion): VWAP от начала бэктеста + k*std(residual) глобально
C) Donchian breakout + ATR trailing stop

Замечания:
- Простая модель исполнения: вход/выход по close бара
- Комиссия (в валюте) и проскальзывание (bps) поддержаны
- Мультипликатор контракта (mult) параметром, по умолчанию 1.0
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Tuple


# -----------------------------
# Utils
# -----------------------------

def _dt(ts_iso: str) -> datetime:
    # ts в БД в формате 2026-03-06T20:49:00 (без TZ) -> считаем UTC
    return datetime.fromisoformat(ts_iso).replace(tzinfo=timezone.utc)

def _date_key(dt: datetime) -> str:
    # UTC day key
    return dt.strftime("%Y-%m-%d")

def _safe_float(x, default=0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


@dataclass(frozen=True)
class Bar:
    ts: datetime
    o: float
    h: float
    l: float
    c: float
    v: float


@dataclass
class Trade:
    strategy: str
    symbol: str
    side: str  # BUY/SELL
    entry_ts: datetime
    entry_px: float
    exit_ts: datetime
    exit_px: float
    qty: float
    pnl: float
    reason: str


# -----------------------------
# Data load
# -----------------------------

def load_bars_sqlite(
    db_path: str,
    *,
    symbol: str,
    timeframe: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> List[Bar]:
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    q = """
    SELECT ts, open, high, low, close, volume
    FROM bars
    WHERE symbol = ? AND timeframe = ?
    """
    args: List = [symbol, timeframe]

    if start is not None:
        q += " AND ts >= ?"
        args.append(start.replace(tzinfo=None).isoformat().replace("+00:00", ""))
    if end is not None:
        q += " AND ts <= ?"
        args.append(end.replace(tzinfo=None).isoformat().replace("+00:00", ""))

    q += " ORDER BY ts ASC"

    out: List[Bar] = []
    for ts, o, h, l, c, v in cur.execute(q, args):
        dt = _dt(ts)
        out.append(Bar(dt, float(o), float(h), float(l), float(c), float(v)))

    con.close()
    return out


def infer_range_from_db(db_path: str, symbol: str, timeframe: str) -> Tuple[Optional[datetime], Optional[datetime], int]:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    row = cur.execute(
        "SELECT min(ts), max(ts), count(*) FROM bars WHERE symbol=? AND timeframe=?",
        (symbol, timeframe),
    ).fetchone()
    con.close()
    if not row:
        return None, None, 0
    mn, mx, n = row
    if mn is None or mx is None:
        return None, None, 0
    return _dt(mn), _dt(mx), int(n)


# -----------------------------
# Execution + accounting
# -----------------------------

@dataclass
class Position:
    side: str  # BUY/SELL
    entry_ts: datetime
    entry_px: float
    qty: float
    stop: Optional[float] = None  # for trailing stop (price level)
    reason: str = ""


def apply_slippage(price: float, side: str, slippage_bps: float) -> float:
    # Русский коммент: bps = 1/10000. BUY ухудшаем вверх, SELL ухудшаем вниз.
    if slippage_bps <= 0:
        return price
    k = slippage_bps / 10000.0
    if side.upper() == "BUY":
        return price * (1.0 + k)
    return price * (1.0 - k)

def trade_pnl(entry_px: float, exit_px: float, side: str, qty: float, mult: float) -> float:
    if side.upper() == "BUY":
        return (exit_px - entry_px) * qty * mult
    return (entry_px - exit_px) * qty * mult


# -----------------------------
# Indicators (incremental)
# -----------------------------

class ATR:
    # Русский коммент: ATR(n) по True Range, сглаживание Wilder.
    def __init__(self, n: int = 14):
        self.n = n
        self.prev_close: Optional[float] = None
        self.atr: Optional[float] = None
        self._count = 0

    def update(self, h: float, l: float, c: float) -> Optional[float]:
        if self.prev_close is None:
            tr = h - l
        else:
            tr = max(h - l, abs(h - self.prev_close), abs(l - self.prev_close))

        self._count += 1

        if self.atr is None:
            # bootstrap: simple average first n TR
            if self._count == 1:
                self.atr = tr
            else:
                self.atr = (self.atr * (self._count - 1) + tr) / self._count
            if self._count >= self.n:
                # switch to Wilder smoothing after n
                pass
        else:
            # Wilder smoothing
            self.atr = (self.atr * (self.n - 1) + tr) / self.n

        self.prev_close = c
        return self.atr


class RunningStd:
    # Русский коммент: std по Welford, без хранения массива.
    def __init__(self):
        self.n = 0
        self.mean = 0.0
        self.m2 = 0.0

    def update(self, x: float) -> None:
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        delta2 = x - self.mean
        self.m2 += delta * delta2

    def std(self) -> float:
        if self.n < 2:
            return 0.0
        return math.sqrt(self.m2 / (self.n - 1))


class VWAP:
    # Русский коммент: VWAP через sum(price*vol)/sum(vol)
    def __init__(self):
        self.pv = 0.0
        self.v = 0.0

    def update(self, price: float, volume: float) -> float:
        v = max(volume, 0.0)
        self.pv += price * v
        self.v += v
        if self.v <= 0:
            return price
        return self.pv / self.v


# -----------------------------
# Strategies
# -----------------------------

class StrategyBase:
    name = "BASE"

    def on_bar(self, bar: Bar, ctx: Dict) -> Tuple[Optional[str], Optional[str]]:
        """
        Возвращает (signal, reason):
        signal: "BUY" | "SELL" | None
        reason: текст причины
        """
        return None, None

    def on_position_bar(self, bar: Bar, pos: Position, ctx: Dict) -> Tuple[bool, str]:
        """
        Возвращает (should_exit, reason)
        """
        return False, ""


class SessionVWAPBands(StrategyBase):
    name = "A_session_vwap_bands"

    def __init__(self, k: float = 2.0, min_points: int = 30, max_trades_per_day: int = 2):
        self.k = k
        self.min_points = min_points
        self.max_trades_per_day = max_trades_per_day
        self._day = None
        self._vwap = VWAP()
        self._resid = RunningStd()
        self._points = 0
        self._trades_today = 0

    def _reset_day(self, day: str):
        self._day = day
        self._vwap = VWAP()
        self._resid = RunningStd()
        self._points = 0
        self._trades_today = 0

    def on_bar(self, bar: Bar, ctx: Dict) -> Tuple[Optional[str], Optional[str]]:
        day = _date_key(bar.ts)
        if self._day != day:
            self._reset_day(day)

        vwap = self._vwap.update(bar.c, bar.v)
        resid = bar.c - vwap
        self._resid.update(resid)
        self._points += 1

        if self._points < self.min_points:
            return None, None
        if self._trades_today >= self.max_trades_per_day:
            return None, None

        s = self._resid.std()
        if s <= 0:
            return None, None

        upper = vwap + self.k * s
        lower = vwap - self.k * s

        # mean reversion: покупаем ниже нижней, продаём выше верхней
        if bar.c < lower:
            self._trades_today += 1
            return "BUY", "below_lower_band"
        if bar.c > upper:
            self._trades_today += 1
            return "SELL", "above_upper_band"

        return None, None

    def on_position_bar(self, bar: Bar, pos: Position, ctx: Dict) -> Tuple[bool, str]:
        # выход: возврат к VWAP (упрощенно)
        day = _date_key(bar.ts)
        if self._day != day:
            # если сменился день — закрываем на первом баре нового дня
            return True, "day_change"

        vwap = self._vwap.pv / self._vwap.v if self._vwap.v > 0 else bar.c

        if pos.side == "BUY" and bar.c >= vwap:
            return True, "revert_to_vwap"
        if pos.side == "SELL" and bar.c <= vwap:
            return True, "revert_to_vwap"

        return False, ""


class AnchoredVWAPBands(StrategyBase):
    name = "B_anchored_vwap_bands"

    def __init__(self, k: float = 2.5, min_points: int = 200):
        self.k = k
        self.min_points = min_points
        self._vwap = VWAP()
        self._resid = RunningStd()
        self._points = 0

    def on_bar(self, bar: Bar, ctx: Dict) -> Tuple[Optional[str], Optional[str]]:
        vwap = self._vwap.update(bar.c, bar.v)
        resid = bar.c - vwap
        self._resid.update(resid)
        self._points += 1

        if self._points < self.min_points:
            return None, None

        s = self._resid.std()
        if s <= 0:
            return None, None

        upper = vwap + self.k * s
        lower = vwap - self.k * s

        if bar.c < lower:
            return "BUY", "below_anchored_lower"
        if bar.c > upper:
            return "SELL", "above_anchored_upper"
        return None, None

    def on_position_bar(self, bar: Bar, pos: Position, ctx: Dict) -> Tuple[bool, str]:
        vwap = self._vwap.pv / self._vwap.v if self._vwap.v > 0 else bar.c
        if pos.side == "BUY" and bar.c >= vwap:
            return True, "revert_to_anchored_vwap"
        if pos.side == "SELL" and bar.c <= vwap:
            return True, "revert_to_anchored_vwap"
        return False, ""


class DonchianATRBreakout(StrategyBase):
    name = "C_donchian_atr_breakout"

    def __init__(self, donchian_n: int = 20, atr_n: int = 14, atr_mult: float = 2.5):
        self.n = donchian_n
        self.atr = ATR(atr_n)
        self.atr_mult = atr_mult
        self._highs: List[float] = []
        self._lows: List[float] = []

    def _donchian(self) -> Tuple[Optional[float], Optional[float]]:
        if len(self._highs) < self.n or len(self._lows) < self.n:
            return None, None
        return max(self._highs[-self.n:]), min(self._lows[-self.n:])

    def on_bar(self, bar: Bar, ctx: Dict) -> Tuple[Optional[str], Optional[str]]:
        # обновим историю ДО сигнала, но используем прошлый канал (без текущего бара)
        self._highs.append(bar.h)
        self._lows.append(bar.l)

        ch, cl = self._donchian()
        a = self.atr.update(bar.h, bar.l, bar.c)

        # Сигнал строим по каналу предыдущих N баров => берем без текущего (сдвиг)
        if len(self._highs) <= self.n:
            return None, None

        prev_ch = max(self._highs[-self.n-1:-1])
        prev_cl = min(self._lows[-self.n-1:-1])

        if bar.c > prev_ch:
            return "BUY", "donchian_breakout_up"
        if bar.c < prev_cl:
            return "SELL", "donchian_breakout_down"
        return None, None

    def on_position_bar(self, bar: Bar, pos: Position, ctx: Dict) -> Tuple[bool, str]:
        a = self.atr.update(bar.h, bar.l, bar.c)
        if a is None:
            return False, ""

        # trailing stop
        if pos.side == "BUY":
            new_stop = bar.c - self.atr_mult * a
            if pos.stop is None:
                pos.stop = new_stop
            else:
                pos.stop = max(pos.stop, new_stop)
            if bar.l <= pos.stop:
                return True, "atr_trailing_stop"
        else:
            new_stop = bar.c + self.atr_mult * a
            if pos.stop is None:
                pos.stop = new_stop
            else:
                pos.stop = min(pos.stop, new_stop)
            if bar.h >= pos.stop:
                return True, "atr_trailing_stop"

        return False, ""


# -----------------------------
# Backtest engine
# -----------------------------

def run_backtest(
    bars: List[Bar],
    *,
    strategy: StrategyBase,
    symbol: str,
    qty: float,
    mult: float,
    commission: float,
    slippage_bps: float,
) -> Tuple[List[Trade], List[Tuple[datetime, float]]]:
    pos: Optional[Position] = None
    trades: List[Trade] = []
    equity = 0.0
    peak = 0.0
    equity_curve: List[Tuple[datetime, float]] = []

    ctx: Dict = {}

    for bar in bars:
        # mark-to-market equity curve per bar (без позы => equity фикс)
        equity_curve.append((bar.ts, equity))

        if pos is not None:
            should_exit, reason = strategy.on_position_bar(bar, pos, ctx)
            if should_exit:
                exit_side = "SELL" if pos.side == "BUY" else "BUY"
                exit_px = apply_slippage(bar.c, exit_side, slippage_bps)

                pnl = trade_pnl(pos.entry_px, exit_px, pos.side, pos.qty, mult)
                # комиссии: комиссия за вход и выход (per-side)
                pnl -= 2.0 * commission

                trades.append(
                    Trade(
                        strategy=strategy.name,
                        symbol=symbol,
                        side=pos.side,
                        entry_ts=pos.entry_ts,
                        entry_px=pos.entry_px,
                        exit_ts=bar.ts,
                        exit_px=exit_px,
                        qty=pos.qty,
                        pnl=pnl,
                        reason=reason,
                    )
                )
                equity += pnl
                pos = None
                continue

        # если позиции нет — ищем вход
        if pos is None:
            sig, reason = strategy.on_bar(bar, ctx)
            if sig in ("BUY", "SELL"):
                entry_px = apply_slippage(bar.c, sig, slippage_bps)
                pos = Position(
                    side=sig,
                    entry_ts=bar.ts,
                    entry_px=entry_px,
                    qty=qty,
                    stop=None,
                    reason=reason or "",
                )

    # закрываем в конце (если позиция осталась)
    if pos is not None and bars:
        bar = bars[-1]
        exit_side = "SELL" if pos.side == "BUY" else "BUY"
        exit_px = apply_slippage(bar.c, exit_side, slippage_bps)
        pnl = trade_pnl(pos.entry_px, exit_px, pos.side, pos.qty, mult) - 2.0 * commission
        trades.append(
            Trade(
                strategy=strategy.name,
                symbol=symbol,
                side=pos.side,
                entry_ts=pos.entry_ts,
                entry_px=pos.entry_px,
                exit_ts=bar.ts,
                exit_px=exit_px,
                qty=pos.qty,
                pnl=pnl,
                reason="eod_forced",
            )
        )
        equity += pnl

    # append final point
    if bars:
        equity_curve.append((bars[-1].ts, equity))

    return trades, equity_curve


# -----------------------------
# Metrics
# -----------------------------

def metrics(trades: List[Trade]) -> Dict[str, float]:
    if not trades:
        return {
            "trades": 0,
            "pnl": 0.0,
            "winrate": 0.0,
            "avg": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "pf": 0.0,
            "expectancy": 0.0,
        }

    pnls = [t.pnl for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    total = sum(pnls)
    n = len(pnls)
    winrate = (len(wins) / n) * 100.0 if n else 0.0
    avg = total / n if n else 0.0
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    pf = (sum(wins) / abs(sum(losses))) if losses else float("inf")

    # expectancy per trade = avg pnl
    return {
        "trades": float(n),
        "pnl": float(total),
        "winrate": float(winrate),
        "avg": float(avg),
        "avg_win": float(avg_win),
        "avg_loss": float(avg_loss),
        "pf": float(pf if math.isfinite(pf) else 9999.0),
        "expectancy": float(avg),
    }


def max_drawdown(equity_curve: List[Tuple[datetime, float]]) -> float:
    peak = -1e18
    mdd = 0.0
    for _, eq in equity_curve:
        peak = max(peak, eq)
        dd = peak - eq
        mdd = max(mdd, dd)
    return float(mdd)


# -----------------------------
# Output
# -----------------------------

def save_trades_csv(path: str, trades: List[Trade]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["strategy", "symbol", "side", "entry_ts", "entry_px", "exit_ts", "exit_px", "qty", "pnl", "reason"])
        for t in trades:
            w.writerow([
                t.strategy,
                t.symbol,
                t.side,
                t.entry_ts.isoformat(),
                f"{t.entry_px:.8f}",
                t.exit_ts.isoformat(),
                f"{t.exit_px:.8f}",
                f"{t.qty:.4f}",
                f"{t.pnl:.8f}",
                t.reason,
            ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.getenv("BARS_DB") or "data/bars.sqlite", help="SQLite path (default: data/bars.sqlite)")
    ap.add_argument("--symbol", default=os.getenv("SYMBOL") or "NGH6@RTSX")
    ap.add_argument("--tf", "--timeframe", dest="tf", default=os.getenv("TIMEFRAME") or "M1")
    ap.add_argument("--days", type=int, default=int(os.getenv("DAYS") or "7"))
    ap.add_argument("--qty", type=float, default=float(os.getenv("QTY") or "1"))
    ap.add_argument("--mult", type=float, default=float(os.getenv("MULT") or "1.0"))
    ap.add_argument("--commission", type=float, default=float(os.getenv("COMMISSION") or "0.0"), help="commission per side, in currency")
    ap.add_argument("--slippage-bps", type=float, default=float(os.getenv("SLIPPAGE_BPS") or "0.0"))

    # strategy params
    ap.add_argument("--a-k", type=float, default=float(os.getenv("A_K") or "2.0"))
    ap.add_argument("--b-k", type=float, default=float(os.getenv("B_K") or "2.5"))
    ap.add_argument("--c-donchian", type=int, default=int(os.getenv("C_DONCHIAN") or "20"))
    ap.add_argument("--c-atr", type=int, default=int(os.getenv("C_ATR") or "14"))
    ap.add_argument("--c-atr-mult", type=float, default=float(os.getenv("C_ATR_MULT") or "2.5"))

    ap.add_argument("--outdir", default=os.getenv("BACKTEST_OUTDIR") or "data/backtests")

    args = ap.parse_args()

    tf = str(args.tf).upper()
    mn, mx, n = infer_range_from_db(args.db, args.symbol, tf)
    if n <= 0 or mn is None or mx is None:
        raise SystemExit(f"No bars in DB for symbol={args.symbol} tf={tf} db={args.db}")

    # берем последние N дней от max(ts)
    end = mx
    start = end - timedelta(days=int(args.days))

    bars = load_bars_sqlite(args.db, symbol=args.symbol, timeframe=tf, start=start, end=end)
    if not bars:
        raise SystemExit("No bars after filtering by days-range")

    print(f"DB={args.db}")
    print(f"SYMBOL={args.symbol} TF={tf} DAYS={args.days} BARS={len(bars)} RANGE={bars[0].ts.isoformat()} .. {bars[-1].ts.isoformat()}")
    print(f"EXEC qty={args.qty} mult={args.mult} commission={args.commission} slippage_bps={args.slippage_bps}")
    print("")

    strategies: List[StrategyBase] = [
        SessionVWAPBands(k=args.a_k),
        AnchoredVWAPBands(k=args.b_k),
        DonchianATRBreakout(donchian_n=args.c_donchian, atr_n=args.c_atr, atr_mult=args.c_atr_mult),
    ]

    rows = []
    for s in strategies:
        trades, eq = run_backtest(
            bars,
            strategy=s,
            symbol=args.symbol,
            qty=args.qty,
            mult=args.mult,
            commission=args.commission,
            slippage_bps=args.slippage_bps,
        )
        m = metrics(trades)
        mdd = max_drawdown(eq)
        rows.append((s.name, m, mdd))

        out_csv = os.path.join(args.outdir, f"{args.symbol}_{tf}_{s.name}_trades.csv")
        save_trades_csv(out_csv, trades)

    # pretty print
    print("RESULTS")
    print("-" * 110)
    print(f"{'strategy':32} | {'trades':>6} | {'pnl':>12} | {'mdd':>12} | {'win%':>6} | {'avg':>12} | {'pf':>8}")
    print("-" * 110)
    for name, m, mdd in rows:
        print(
            f"{name:32} | "
            f"{int(m['trades']):6d} | "
            f"{m['pnl']:12.6f} | "
            f"{mdd:12.6f} | "
            f"{m['winrate']:6.2f} | "
            f"{m['avg']:12.6f} | "
            f"{m['pf']:8.2f}"
        )
    print("-" * 110)
    print(f"CSV saved to: {args.outdir}/ (per-strategy trades)")
    print("")


if __name__ == "__main__":
    main()
