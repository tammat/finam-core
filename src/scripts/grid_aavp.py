# -*- coding: utf-8 -*-
"""
Grid search для AAVP (Volume Profile) стратегии на данных из SQLite.

Метрики:
- net_pnl: итоговая прибыль/убыток
- max_dd: максимальная просадка по equity curve (абс. в валюте счета)
- score: net_pnl / (1 + max_dd)  (простая нормировка; чем выше, тем лучше)

Русский коммент: без внешних зависимостей (pandas не нужен).
"""

from __future__ import annotations

import argparse
import csv
import math
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class Bar:
    ts: str
    o: float
    h: float
    l: float
    c: float
    v: float


@dataclass
class GridRow:
    window: int
    bin_size: float
    enter_k: float
    stop_k: float
    value_area_pct: float
    trades: int
    net_pnl: float
    max_dd: float
    win_rate: float
    score: float


def load_bars_sqlite(db_path: str, symbol: str, tf: str) -> List[Bar]:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(
        """
        SELECT ts, open, high, low, close, volume
        FROM bars
        WHERE symbol = ? AND timeframe = ?
        ORDER BY ts ASC
        """,
        (symbol, tf),
    )
    rows = cur.fetchall()
    con.close()

    bars: List[Bar] = []
    for ts, o, h, l, c, v in rows:
        bars.append(Bar(str(ts), float(o), float(h), float(l), float(c), float(v)))
    return bars


def _apply_slippage(px: float, side: str, slippage_bps: float) -> float:
    """Русский коммент: slippage_bps=2 => 0.02%."""
    s = float(slippage_bps) / 10_000.0
    if side.upper() == "BUY":
        return px * (1.0 + s)
    return px * (1.0 - s)


def _max_drawdown(eq: List[Tuple[str, float]]) -> float:
    peak = -1e100
    max_dd = 0.0
    for _, e in eq:
        if e > peak:
            peak = e
        dd = peak - e
        if dd > max_dd:
            max_dd = dd
    return float(max_dd)


def _winrate(pnls: List[float]) -> float:
    if not pnls:
        return 0.0
    wins = sum(1 for x in pnls if x > 0)
    return wins / len(pnls)


def _profile_levels_from_window(
    closes: List[float],
    volumes: List[float],
    *,
    bin_size: float,
    value_area_pct: float = 0.70,
) -> Tuple[float, float, float]:
    assert bin_size > 0

    bins: Dict[int, float] = {}
    for p, v in zip(closes, volumes):
        b = int(round(p / bin_size))
        bins[b] = bins.get(b, 0.0) + float(v or 0.0)

    if not bins:
        px = closes[-1]
        return px, px, px

    poc_bin = max(bins.items(), key=lambda kv: kv[1])[0]
    total_vol = sum(bins.values())
    target = total_vol * float(value_area_pct)

    included = {poc_bin}
    acc = bins[poc_bin]

    left = poc_bin - 1
    right = poc_bin + 1
    while acc < target and (left in bins or right in bins):
        lv = bins.get(left, -1.0)
        rv = bins.get(right, -1.0)
        if rv >= lv:
            if right in bins:
                included.add(right)
                acc += bins[right]
            right += 1
        else:
            if left in bins:
                included.add(left)
                acc += bins[left]
            left -= 1

    val_bin = min(included)
    vah_bin = max(included)

    poc = poc_bin * bin_size
    val = val_bin * bin_size
    vah = vah_bin * bin_size
    return poc, vah, val


def backtest_aavp_profile_reversion(
    bars: List[Bar],
    *,
    initial_cash: float,
    commission: float,
    slippage_bps: float,
    mult: float,
    window: int,
    bin_size: float,
    value_area_pct: float,
    enter_k: float,
    stop_k: float,
) -> Tuple[int, float, float, float]:
    """
    Возвращает:
    trades_count, net_pnl, max_dd, win_rate
    """
    cash = float(initial_cash)
    pos = 0
    entry_px = 0.0
    entry_ts = ""
    pnls: List[float] = []
    eq: List[Tuple[str, float]] = []

    closes: List[float] = []
    vols: List[float] = []

    for i, b in enumerate(bars):
        closes.append(b.c)
        vols.append(b.v)

        # MTM
        equity = cash + (b.c - entry_px) * mult if pos == 1 else cash
        eq.append((b.ts, equity))

        if i < window:
            continue

        w_cl = closes[-window:]
        w_v = vols[-window:]

        poc, vah, val = _profile_levels_from_window(
            w_cl, w_v, bin_size=bin_size, value_area_pct=value_area_pct
        )
        va_range = max(vah - val, 1e-12)

        enter_lvl = val - enter_k * va_range
        stop_lvl = val - stop_k * va_range

        # exit
        if pos == 1:
            if b.c >= poc or b.c <= stop_lvl:
                px = _apply_slippage(b.c, "SELL", slippage_bps)
                pnl = (px - entry_px) * mult
                cash += pnl
                cash -= commission
                pnls.append(pnl - 2 * commission)
                pos = 0

        # entry
        if pos == 0:
            if b.c <= enter_lvl:
                px = _apply_slippage(b.c, "BUY", slippage_bps)
                cash -= commission
                entry_px = px
                entry_ts = b.ts
                pos = 1

    # close at end
    if pos == 1:
        b = bars[-1]
        px = _apply_slippage(b.c, "SELL", slippage_bps)
        pnl = (px - entry_px) * mult
        cash += pnl
        cash -= commission
        pnls.append(pnl - 2 * commission)

    net = cash - initial_cash
    max_dd = _max_drawdown(eq)
    wr = _winrate(pnls)
    return len(pnls), float(net), float(max_dd), float(wr)


def parse_list_int(s: str) -> List[int]:
    out = []
    for x in s.split(","):
        x = x.strip()
        if not x:
            continue
        out.append(int(x))
    return out


def parse_list_float(s: str) -> List[float]:
    out = []
    for x in s.split(","):
        x = x.strip()
        if not x:
            continue
        out.append(float(x))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/bars.sqlite")
    ap.add_argument("--symbol", default="NGH6@RTSX")
    ap.add_argument("--tf", default="M1")

    ap.add_argument("--initial", type=float, default=100_000.0)
    ap.add_argument("--commission", type=float, default=1.5)     # per execution
    ap.add_argument("--slippage-bps", type=float, default=2.0)
    ap.add_argument("--mult", type=float, default=1.0)          # пока 1.0, позже подставим реальный multiplier

    ap.add_argument("--windows", default="300,600,1200")
    ap.add_argument("--bins", default="0.001,0.0005")
    ap.add_argument("--enter-ks", default="0.10,0.20,0.30")
    ap.add_argument("--stop-ks", default="0.50,0.60,0.80")
    ap.add_argument("--va", type=float, default=0.70)

    ap.add_argument("--maxdd-cap", type=float, default=999999999.0, help="Фильтр по max_dd (абсолют)")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--out", default="data/grid_aavp_results.csv")
    args = ap.parse_args()

    bars = load_bars_sqlite(args.db, args.symbol, args.tf)
    if len(bars) < 100:
        raise SystemExit(f"Not enough bars: {len(bars)}")

    windows = parse_list_int(args.windows)
    bins = parse_list_float(args.bins)
    enter_ks = parse_list_float(args.enter_ks)
    stop_ks = parse_list_float(args.stop_ks)

    rows: List[GridRow] = []

    for w in windows:
        for b in bins:
            for ek in enter_ks:
                for sk in stop_ks:
                    trades, net, max_dd, wr = backtest_aavp_profile_reversion(
                        bars,
                        initial_cash=args.initial,
                        commission=args.commission,
                        slippage_bps=args.slippage_bps,
                        mult=args.mult,
                        window=w,
                        bin_size=b,
                        value_area_pct=args.va,
                        enter_k=ek,
                        stop_k=sk,
                    )
                    if max_dd > args.maxdd_cap:
                        continue

                    score = net / (1.0 + max_dd)
                    rows.append(
                        GridRow(
                            window=w,
                            bin_size=b,
                            enter_k=ek,
                            stop_k=sk,
                            value_area_pct=args.va,
                            trades=trades,
                            net_pnl=net,
                            max_dd=max_dd,
                            win_rate=wr,
                            score=score,
                        )
                    )

    # save CSV
    import os
    os.makedirs(os.path.dirname(args.out), exist_ok=True) if os.path.dirname(args.out) else None
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        wri = csv.writer(f)
        wri.writerow(["window", "bin", "enter_k", "stop_k", "va", "trades", "net_pnl", "max_dd", "win_rate", "score"])
        for r in rows:
            wri.writerow([r.window, r.bin_size, r.enter_k, r.stop_k, r.value_area_pct, r.trades, r.net_pnl, r.max_dd, r.win_rate, r.score])

    # Top by net
    top_net = sorted(rows, key=lambda r: r.net_pnl, reverse=True)[: args.top]
    # Top by score
    top_score = sorted(rows, key=lambda r: r.score, reverse=True)[: args.top]
    # Low DD (for reference)
    top_dd = sorted(rows, key=lambda r: r.max_dd)[: args.top]

    def _print(title: str, lst: List[GridRow]):
        print("\n" + title)
        print("window bin enter_k stop_k trades net_pnl max_dd win_rate score")
        for r in lst:
            print(
                f"{r.window:>5} {r.bin_size:<7g} {r.enter_k:<6g} {r.stop_k:<6g} "
                f"{r.trades:>6} {r.net_pnl:>10.2f} {r.max_dd:>10.2f} {r.win_rate:>7.2%} {r.score:>10.6f}"
            )

    _print(f"TOP {args.top} by NET (maxdd_cap={args.maxdd_cap})", top_net)
    _print(f"TOP {args.top} by SCORE=net/(1+dd)", top_score)
    _print(f"TOP {args.top} by MIN DRAWDOWN", top_dd)

    print("\nCSV saved:", args.out)


if __name__ == "__main__":
    main()