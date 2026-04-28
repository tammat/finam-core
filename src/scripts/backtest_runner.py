# -*- coding: utf-8 -*-
"""
backtest_runner.py — читает bars из SQLite и пишет результаты прогонов в SQLite.

Таблицы:
- bars(symbol,timeframe,ts,open,high,low,close,volume)  <-- уже есть
- backtest_runs(...)                                   <-- создаём здесь
- backtest_trades(...)                                 <-- опционально (включается --save-trades)

Поддерживаем стратегии (минимально, но практично):
1) vwap_bands_mr  — mean reversion от VWAP с полосами std (окно N, k)
2) donchian_break — пробой канала Дончиана (окно N)
3) ema_cross      — пересечение EMA fast/slow

Параметры прогонов:
- grid: window/fast/slow/k/stop_pct/take_pct и т.п.
- выбираем топ по Net и MaxDD уже SQL-запросом после прогонов.

Русские комментарии — у критичных мест.
"""

import os
import json
import math
import uuid
import sqlite3
import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional

import pandas as pd


# -------------------------
# SQLite schema
# -------------------------
def ensure_results_schema(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS backtest_runs (
            run_id TEXT PRIMARY KEY,
            ts_run TEXT NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            strategy TEXT NOT NULL,
            params_json TEXT NOT NULL,
            start_ts TEXT NOT NULL,
            end_ts TEXT NOT NULL,

            net_pnl REAL NOT NULL,
            gross_pnl REAL NOT NULL,
            max_dd REAL NOT NULL,
            max_dd_pct REAL NOT NULL,

            trades INTEGER NOT NULL,
            wins INTEGER NOT NULL,
            win_rate REAL NOT NULL,
            profit_factor REAL NOT NULL,

            exposure_pct REAL NOT NULL,
            sharpe REAL NOT NULL
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS backtest_trades (
            trade_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            side TEXT NOT NULL,
            qty REAL NOT NULL,
            entry_ts TEXT NOT NULL,
            entry_price REAL NOT NULL,
            exit_ts TEXT NOT NULL,
            exit_price REAL NOT NULL,
            pnl_gross REAL NOT NULL,
            pnl_net REAL NOT NULL,
            commission REAL NOT NULL,
            slippage REAL NOT NULL,
            FOREIGN KEY(run_id) REFERENCES backtest_runs(run_id)
        )
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS ix_backtest_runs_sym_tf ON backtest_runs(symbol,timeframe)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_backtest_trades_run ON backtest_trades(run_id)")
    con.commit()


def load_bars(
    con: sqlite3.Connection,
    *,
    symbol: str,
    timeframe: str,
    start_ts: Optional[str] = None,
    end_ts: Optional[str] = None,
) -> pd.DataFrame:
    q = """
    SELECT ts, open, high, low, close, volume
    FROM bars
    WHERE symbol=? AND timeframe=?
    """
    params = [symbol, timeframe]

    if start_ts:
        q += " AND ts >= ?"
        params.append(start_ts)
    if end_ts:
        q += " AND ts <= ?"
        params.append(end_ts)

    q += " ORDER BY ts ASC"

    df = pd.read_sql_query(q, con, params=params)
    if df.empty:
        raise RuntimeError(f"Нет баров в SQLite для {symbol} {timeframe} диапазон start={start_ts} end={end_ts}")

    # Русский коммент: ts храним как ISO-строку; для расчётов переводим в datetime (UTC)
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df = df.dropna(subset=["ts"]).reset_index(drop=True)

    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    return df


# -------------------------
# Backtest engine
# -------------------------
@dataclass
class Trade:
    side: str              # "LONG" or "SHORT"
    qty: float
    entry_ts: datetime
    entry_price: float
    exit_ts: datetime
    exit_price: float
    pnl_gross: float
    pnl_net: float
    commission: float
    slippage: float


def max_drawdown(equity: pd.Series) -> Tuple[float, float]:
    peak = equity.cummax()
    dd = equity - peak
    max_dd = float(dd.min())  # отрицательное
    max_dd_pct = float((dd / peak.replace(0, math.nan)).min())
    if math.isnan(max_dd_pct):
        max_dd_pct = 0.0
    return max_dd, max_dd_pct


def sharpe_ratio(returns: pd.Series, bars_per_year: float) -> float:
    # Русский коммент: примитивно; для сравнения конфигов достаточно
    r = returns.dropna()
    if len(r) < 5:
        return 0.0
    mu = r.mean()
    sd = r.std(ddof=1)
    if sd == 0 or math.isnan(sd):
        return 0.0
    return float((mu / sd) * math.sqrt(bars_per_year))


def estimate_bars_per_year(timeframe: str) -> float:
    tf = timeframe.upper()
    # грубо для фьючей/акций: берём торговые дни ~252, минут в сессии ~ 600 (10 часов)
    if tf == "M1":
        return 252 * 600
    if tf == "M5":
        return 252 * (600 / 5)
    if tf == "M15":
        return 252 * (600 / 15)
    if tf == "H1":
        return 252 * 10
    if tf == "D1":
        return 252
    return 252 * 600


def apply_costs(price: float, side: str, slippage_bps: float) -> float:
    """
    Русский коммент:
    slippage_bps = 1.0 => 1 базисный пункт = 0.01%,
    для BUY цена чуть хуже, для SELL тоже хуже (в сторону уменьшения pnl).
    """
    if slippage_bps <= 0:
        return price
    slip = price * (slippage_bps / 10000.0)
    if side == "BUY":
        return price + slip
    else:
        return price - slip


def run_backtest(
    df: pd.DataFrame,
    *,
    strategy: str,
    params: Dict[str, Any],
    starting_cash: float,
    qty: float,
    commission_per_trade: float,
    slippage_bps: float,
    allow_short: bool,
) -> Tuple[Dict[str, Any], List[Trade]]:
    """
    Возвращает:
    - metrics
    - trades list (если надо сохранить)
    """

    close = df["close"]
    high = df["high"]
    low = df["low"]
    ts = df["ts"]

    pos = 0            # +1 long, -1 short, 0 flat
    entry_px = 0.0
    entry_ts = None

    daily_loss_limit = float(params.get("daily_loss_limit", 0.0) or 0.0)
    current_trade_day = None
    day_realized_pnl = 0.0
    day_blocked = False

    equity = starting_cash
    equity_curve = []
    in_pos_bars = 0
    trades: List[Trade] = []

    # стратегия-сигналы
    strat = strategy.lower()

    # -------------------------
    # Indicators
    # -------------------------
    if strat == "vwap_bands_mr":
        w = int(params.get("window", 200))
        k = float(params.get("k", 2.0))

        # VWAP = sum(price*vol)/sum(vol) по окну
        vol = df["volume"].fillna(0.0)
        pv = close * vol
        vwap = pv.rolling(w).sum() / vol.rolling(w).sum().replace(0, math.nan)
        std = close.rolling(w).std(ddof=1)
        upper = vwap + k * std
        lower = vwap - k * std

        # exit: возврат к vwap
        # entry long: close < lower, entry short: close > upper (если allow_short)
        # optional stops
        stop_pct = float(params.get("stop_pct", 0.0))
        take_pct = float(params.get("take_pct", 0.0))

        # Русский коммент: режимный MR-фильтр — не открываем сделки, если цена слишком далеко от EMA.
        mr_ema_n = int(params.get("mr_ema", 0) or 0)
        mr_max_dev = float(params.get("mr_max_dev", 0.0) or 0.0)
        mr_ema = close.ewm(span=mr_ema_n, adjust=False).mean() if mr_ema_n > 0 else None

        # Русский коммент: сессионный фильтр. Пока используем day как торговые часы 06:00-18:59 UTC.
        session = str(params.get("session", "") or "").strip().lower()

        def session_allows(i: int) -> bool:
            if session in ("", "all"):
                return True
            if session == "day":
                hour = ts.iat[i].hour
                return 6 <= hour < 19
            return True

        def mr_regime_allows(i: int) -> bool:
            if mr_ema is not None and mr_max_dev > 0:
                if pd.isna(mr_ema.iat[i]) or mr_ema.iat[i] == 0:
                    return False
                dev = abs(float(close.iat[i]) - float(mr_ema.iat[i])) / abs(float(mr_ema.iat[i]))
                if dev > mr_max_dev:
                    return False
            return True

        # Русский коммент: Regime Layer v1 — ATR-фильтр волатильности.
        regime_layer = str(params.get("regime_layer", "") or "").strip().lower()
        regime_atr_n = int(params.get("regime_atr_n", 14) or 14)
        regime_atr_mode = str(params.get("regime_atr_mode", "percentile") or "percentile").strip().lower()
        regime_atr_threshold = float(params.get("regime_atr_threshold", 0.0) or 0.0)
        regime_atr_pct_window = int(params.get("regime_atr_pct_window", 100) or 100)
        regime_ema_slope = str(params.get("regime_ema_slope", "") or "").strip().lower()
        regime_ema_slope_enabled = regime_ema_slope == "on"
        regime_ema_slope_lookback = int(params.get("regime_ema_slope_lookback", 20) or 20)
        regime_ema_slope_threshold = float(params.get("regime_ema_slope_threshold", 0.002) or 0.002)

        prev_close = close.shift(1)
        tr1 = (df["high"] - df["low"]).abs()
        tr2 = (df["high"] - prev_close).abs()
        tr3 = (df["low"] - prev_close).abs()
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        regime_atr = true_range.rolling(regime_atr_n).mean()
        regime_atr_pct = regime_atr.rolling(regime_atr_pct_window).rank(pct=True)

        def regime_allows(i: int) -> bool:
            if regime_layer in ("", "off", "none"):
                return True
            if regime_layer != "atr":
                return True
            if regime_atr_threshold <= 0:
                return True

            if regime_atr_mode in ("", "percentile"):
                value = regime_atr_pct.iat[i]
                if pd.isna(value):
                    return False
                return float(value) <= regime_atr_threshold

            if regime_atr_mode == "absolute":
                value = regime_atr.iat[i]
                if pd.isna(value):
                    return False
                return float(value) <= regime_atr_threshold

            return True

        # -------------------- EMA SLOPE REGIME --------------------
        def ema_slope_allows(i: int) -> bool:
            # Русский коммент:
            # Фильтр отключает mean-reversion, если EMA имеет сильный наклон (тренд)

            if not regime_ema_slope_enabled:
                return True

            if i < regime_ema_slope_lookback:
                return True

            if mr_ema is None:
                return True

            ema_now = mr_ema.iat[i]
            ema_prev = mr_ema.iat[i - regime_ema_slope_lookback]

            if pd.isna(ema_now) or pd.isna(ema_prev):
                return True

            slope = (ema_now - ema_prev) / ema_prev

            # абсолютный наклон
            return abs(float(slope)) <= regime_ema_slope_threshold

        def entry_filters_allow(i: int) -> bool:
            return (
                    session_allows(i)
                    and mr_regime_allows(i)
                    and regime_allows(i)
                    and ema_slope_allows(i)
            )

        def want_long(i: int) -> bool:
            return entry_filters_allow(i) and pd.notna(lower.iat[i]) and close.iat[i] < lower.iat[i]

        def want_short(i: int) -> bool:
            return allow_short and entry_filters_allow(i) and pd.notna(upper.iat[i]) and close.iat[i] > upper.iat[i]

        def exit_long(i: int) -> bool:
            return pd.notna(vwap.iat[i]) and close.iat[i] >= vwap.iat[i]

        def exit_short(i: int) -> bool:
            return pd.notna(vwap.iat[i]) and close.iat[i] <= vwap.iat[i]

    elif strat == "donchian_break":
        w = int(params.get("window", 120))
        hh = high.rolling(w).max()
        ll = low.rolling(w).min()
        stop_pct = float(params.get("stop_pct", 0.0))
        take_pct = float(params.get("take_pct", 0.0))

        def want_long(i: int) -> bool:
            return pd.notna(hh.iat[i]) and close.iat[i] > hh.iat[i - 1] if i > 0 else False

        def want_short(i: int) -> bool:
            return allow_short and pd.notna(ll.iat[i]) and close.iat[i] < ll.iat[i - 1] if i > 0 else False

        def exit_long(i: int) -> bool:
            return pd.notna(ll.iat[i]) and close.iat[i] < ll.iat[i]

        def exit_short(i: int) -> bool:
            return pd.notna(hh.iat[i]) and close.iat[i] > hh.iat[i]

    elif strat == "ema_cross":
        fast = int(params.get("fast", 20))
        slow = int(params.get("slow", 60))
        if fast >= slow:
            raise RuntimeError("ema_cross: fast must be < slow")
        ema_f = close.ewm(span=fast, adjust=False).mean()
        ema_s = close.ewm(span=slow, adjust=False).mean()
        stop_pct = float(params.get("stop_pct", 0.0))
        take_pct = float(params.get("take_pct", 0.0))

        def want_long(i: int) -> bool:
            if i == 0:
                return False
            return ema_f.iat[i - 1] <= ema_s.iat[i - 1] and ema_f.iat[i] > ema_s.iat[i]

        def want_short(i: int) -> bool:
            if not allow_short or i == 0:
                return False
            return ema_f.iat[i - 1] >= ema_s.iat[i - 1] and ema_f.iat[i] < ema_s.iat[i]

        def exit_long(i: int) -> bool:
            if i == 0:
                return False
            return ema_f.iat[i - 1] >= ema_s.iat[i - 1] and ema_f.iat[i] < ema_s.iat[i]

        def exit_short(i: int) -> bool:
            if i == 0:
                return False
            return ema_f.iat[i - 1] <= ema_s.iat[i - 1] and ema_f.iat[i] > ema_s.iat[i]

    else:
        raise RuntimeError(f"Unknown strategy={strategy}")

    # -------------------------
    # Loop
    # -------------------------
    for i in range(len(df)):
        px = float(close.iat[i])
        t = ts.iat[i].to_pydatetime()

        trade_day = t.strftime("%Y-%m-%d")
        if current_trade_day != trade_day:
            current_trade_day = trade_day
            day_realized_pnl = 0.0
            day_blocked = False

        # mark-to-market equity (без учёта costs пока)
        mtm = 0.0
        if pos != 0:
            in_pos_bars += 1
            if pos > 0:
                mtm = (px - entry_px) * qty
            else:
                mtm = (entry_px - px) * qty
        equity_curve.append(equity + mtm)

        # skip until indicators warmup
        # (косвенно: want_long/short будут False если NaN)
        # exit logic first
        if pos != 0:
            # stop/take (процент от entry)
            if stop_pct > 0:
                if pos > 0 and px <= entry_px * (1.0 - stop_pct):
                    # exit long by stop
                    exit_side = "SELL"
                    exit_px = apply_costs(px, exit_side, slippage_bps)
                    entry_cost_px = apply_costs(entry_px, "BUY", slippage_bps)
                    pnl_gross = (exit_px - entry_cost_px) * qty
                    commission = commission_per_trade * 2.0
                    pnl_net = pnl_gross - commission
                    equity += pnl_net
                    day_realized_pnl += pnl_net
                    if daily_loss_limit > 0 and day_realized_pnl <= -daily_loss_limit:
                        day_blocked = True
                    trades.append(Trade("LONG", qty, entry_ts, entry_px, t, px, pnl_gross, pnl_net, commission, 2.0 * abs(px) * (slippage_bps / 10000.0)))
                    pos = 0
                    entry_px = 0.0
                    entry_ts = None
                    continue
                if pos < 0 and px >= entry_px * (1.0 + stop_pct):
                    # exit short by stop
                    exit_side = "BUY"
                    exit_px = apply_costs(px, exit_side, slippage_bps)
                    entry_cost_px = apply_costs(entry_px, "SELL", slippage_bps)
                    pnl_gross = (entry_cost_px - exit_px) * qty
                    commission = commission_per_trade * 2.0
                    pnl_net = pnl_gross - commission
                    equity += pnl_net
                    day_realized_pnl += pnl_net
                    if daily_loss_limit > 0 and day_realized_pnl <= -daily_loss_limit:
                        day_blocked = True
                    trades.append(Trade("SHORT", qty, entry_ts, entry_px, t, px, pnl_gross, pnl_net, commission, 2.0 * abs(px) * (slippage_bps / 10000.0)))
                    pos = 0
                    entry_px = 0.0
                    entry_ts = None
                    continue

            if take_pct > 0:
                if pos > 0 and px >= entry_px * (1.0 + take_pct):
                    exit_side = "SELL"
                    exit_px = apply_costs(px, exit_side, slippage_bps)
                    entry_cost_px = apply_costs(entry_px, "BUY", slippage_bps)
                    pnl_gross = (exit_px - entry_cost_px) * qty
                    commission = commission_per_trade * 2.0
                    pnl_net = pnl_gross - commission
                    equity += pnl_net
                    day_realized_pnl += pnl_net
                    if daily_loss_limit > 0 and day_realized_pnl <= -daily_loss_limit:
                        day_blocked = True
                    trades.append(Trade("LONG", qty, entry_ts, entry_px, t, px, pnl_gross, pnl_net, commission, 2.0 * abs(px) * (slippage_bps / 10000.0)))
                    pos = 0
                    entry_px = 0.0
                    entry_ts = None
                    continue
                if pos < 0 and px <= entry_px * (1.0 - take_pct):
                    exit_side = "BUY"
                    exit_px = apply_costs(px, exit_side, slippage_bps)
                    entry_cost_px = apply_costs(entry_px, "SELL", slippage_bps)
                    pnl_gross = (entry_cost_px - exit_px) * qty
                    commission = commission_per_trade * 2.0
                    pnl_net = pnl_gross - commission
                    equity += pnl_net
                    day_realized_pnl += pnl_net
                    if daily_loss_limit > 0 and day_realized_pnl <= -daily_loss_limit:
                        day_blocked = True
                    trades.append(Trade("SHORT", qty, entry_ts, entry_px, t, px, pnl_gross, pnl_net, commission, 2.0 * abs(px) * (slippage_bps / 10000.0)))
                    pos = 0
                    entry_px = 0.0
                    entry_ts = None
                    continue

            # indicator exits
            if pos > 0 and exit_long(i):
                exit_side = "SELL"
                exit_px = apply_costs(px, exit_side, slippage_bps)
                entry_cost_px = apply_costs(entry_px, "BUY", slippage_bps)
                pnl_gross = (exit_px - entry_cost_px) * qty
                commission = commission_per_trade * 2.0
                pnl_net = pnl_gross - commission
                equity += pnl_net
                day_realized_pnl += pnl_net
                if daily_loss_limit > 0 and day_realized_pnl <= -daily_loss_limit:
                    day_blocked = True
                trades.append(Trade("LONG", qty, entry_ts, entry_px, t, px, pnl_gross, pnl_net, commission, 2.0 * abs(px) * (slippage_bps / 10000.0)))
                pos = 0
                entry_px = 0.0
                entry_ts = None
                continue

            if pos < 0 and exit_short(i):
                exit_side = "BUY"
                exit_px = apply_costs(px, exit_side, slippage_bps)
                entry_cost_px = apply_costs(entry_px, "SELL", slippage_bps)
                pnl_gross = (entry_cost_px - exit_px) * qty
                commission = commission_per_trade * 2.0
                pnl_net = pnl_gross - commission
                equity += pnl_net
                day_realized_pnl += pnl_net
                if daily_loss_limit > 0 and day_realized_pnl <= -daily_loss_limit:
                    day_blocked = True
                trades.append(Trade("SHORT", qty, entry_ts, entry_px, t, px, pnl_gross, pnl_net, commission, 2.0 * abs(px) * (slippage_bps / 10000.0)))
                pos = 0
                entry_px = 0.0
                entry_ts = None
                continue

        # entry logic (если flat)
        if pos == 0 and not day_blocked:
            if want_long(i):
                pos = 1
                entry_px = px
                entry_ts = t
                continue
            if want_short(i):
                pos = -1
                entry_px = px
                entry_ts = t
                continue

    # close position at last bar (если осталась)
    if pos != 0 and entry_ts is not None:
        px = float(close.iat[-1])
        t = ts.iat[-1].to_pydatetime()
        if pos > 0:
            exit_side = "SELL"
            exit_px = apply_costs(px, exit_side, slippage_bps)
            entry_cost_px = apply_costs(entry_px, "BUY", slippage_bps)
            pnl_gross = (exit_px - entry_cost_px) * qty
            commission = commission_per_trade * 2.0
            pnl_net = pnl_gross - commission
            equity += pnl_net
            trades.append(Trade("LONG", qty, entry_ts, entry_px, t, px, pnl_gross, pnl_net, commission, 2.0 * abs(px) * (slippage_bps / 10000.0)))
        else:
            exit_side = "BUY"
            exit_px = apply_costs(px, exit_side, slippage_bps)
            entry_cost_px = apply_costs(entry_px, "SELL", slippage_bps)
            pnl_gross = (entry_cost_px - exit_px) * qty
            commission = commission_per_trade * 2.0
            pnl_net = pnl_gross - commission
            equity += pnl_net
            trades.append(Trade("SHORT", qty, entry_ts, entry_px, t, px, pnl_gross, pnl_net, commission, 2.0 * abs(px) * (slippage_bps / 10000.0)))

    # metrics
    eq = pd.Series(equity_curve, dtype="float64")
    dd, dd_pct = max_drawdown(eq)
    gross = float(sum(t.pnl_gross for t in trades))
    net = float(sum(t.pnl_net for t in trades))

    wins = sum(1 for t in trades if t.pnl_net > 0)
    losses = sum(1 for t in trades if t.pnl_net < 0)
    win_rate = float(wins / len(trades)) if trades else 0.0

    pos_pnl = sum(t.pnl_net for t in trades if t.pnl_net > 0)
    neg_pnl = -sum(t.pnl_net for t in trades if t.pnl_net < 0)
    profit_factor = float(pos_pnl / neg_pnl) if neg_pnl > 0 else (float("inf") if pos_pnl > 0 else 0.0)

    # returns for sharpe (equity changes)
    ret = eq.pct_change()
    sh = sharpe_ratio(ret, estimate_bars_per_year(params.get("timeframe", "M1")))

    exposure_pct = float(in_pos_bars / len(df)) if len(df) else 0.0

    metrics = dict(
        net_pnl=net,
        gross_pnl=gross,
        max_dd=dd,
        max_dd_pct=dd_pct,
        trades=len(trades),
        wins=wins,
        win_rate=win_rate,
        profit_factor=profit_factor if math.isfinite(profit_factor) else 999.0,
        exposure_pct=exposure_pct,
        sharpe=sh,
    )
    return metrics, trades


# -------------------------
# Grid
# -------------------------
def parse_list(s: str, cast=float) -> List:
    # "10,20,30"
    return [cast(x.strip()) for x in s.split(",") if x.strip()]


def grid_params(strategy: str, args) -> List[Dict[str, Any]]:
    strat = strategy.lower()
    out: List[Dict[str, Any]] = []

    if strat == "vwap_bands_mr":
        windows = parse_list(args.window, int)
        ks = parse_list(args.k, float)
        stops = parse_list(args.stop_pct, float) if args.stop_pct else [0.0]
        takes = parse_list(args.take_pct, float) if args.take_pct else [0.0]
        sessions = parse_list(args.session, str) if getattr(args, "session", "") else [""]
        mr_emas = parse_list(args.mr_ema, int) if getattr(args, "mr_ema", "") else [0]
        mr_max_devs = parse_list(args.mr_max_dev, float) if getattr(args, "mr_max_dev", "") else [0.0]
        daily_loss_limits = parse_list(args.daily_loss_limit, float) if getattr(args, "daily_loss_limit", "") else [0.0]
        regime_layers = parse_list(args.regime_layer, str) if getattr(args, "regime_layer", "") else [""]
        regime_atr_ns = parse_list(args.regime_atr_n, int) if getattr(args, "regime_atr_n", "") else [14]
        regime_atr_modes = parse_list(args.regime_atr_mode, str) if getattr(args, "regime_atr_mode", "") else ["percentile"]
        regime_atr_thresholds = parse_list(args.regime_atr_threshold, float) if getattr(args, "regime_atr_threshold", "") else [0.0]
        regime_atr_pct_windows = parse_list(args.regime_atr_pct_window, int) if getattr(args, "regime_atr_pct_window", "") else [100]
        regime_ema_slopes = parse_list(args.regime_ema_slope, str) if getattr(args, "regime_ema_slope", "") else [""]
        regime_ema_slope_lookbacks = parse_list(args.regime_ema_slope_lookback, int) if getattr(args, "regime_ema_slope_lookback", "") else [20]
        regime_ema_slope_thresholds = parse_list(args.regime_ema_slope_threshold, float) if getattr(args, "regime_ema_slope_threshold", "") else [0.002]
        for w in windows:
            for k in ks:
                for sp in stops:
                    for tp in takes:
                        for session in sessions:
                            for mr_ema in mr_emas:
                                for mr_max_dev in mr_max_devs:
                                    for daily_loss_limit in daily_loss_limits:
                                        for regime_layer in regime_layers:
                                            for regime_atr_n in regime_atr_ns:
                                                for regime_atr_mode in regime_atr_modes:
                                                    for regime_atr_threshold in regime_atr_thresholds:
                                                        for regime_atr_pct_window in regime_atr_pct_windows:
                                                            for regime_ema_slope in regime_ema_slopes:
                                                                for regime_ema_slope_lookback in regime_ema_slope_lookbacks:
                                                                    for regime_ema_slope_threshold in regime_ema_slope_thresholds:
                                                                        out.append({
                                                                            "window": w,
                                                                            "k": k,
                                                                            "stop_pct": sp,
                                                                            "take_pct": tp,
                                                                            "session": session,
                                                                            "mr_ema": mr_ema,
                                                                            "mr_max_dev": mr_max_dev,
                                                                            "daily_loss_limit": daily_loss_limit,
                                                                            "regime_layer": regime_layer,
                                                                            "regime_atr_n": regime_atr_n,
                                                                            "regime_atr_mode": regime_atr_mode,
                                                                            "regime_atr_threshold": regime_atr_threshold,
                                                                            "regime_atr_pct_window": regime_atr_pct_window,
                                                                            "regime_ema_slope": regime_ema_slope,
                                                                            "regime_ema_slope_lookback": regime_ema_slope_lookback,
                                                                            "regime_ema_slope_threshold": regime_ema_slope_threshold,
                                                                        })
        return out

    if strat == "donchian_break":
        windows = parse_list(args.window, int)
        stops = parse_list(args.stop_pct, float) if args.stop_pct else [0.0]
        takes = parse_list(args.take_pct, float) if args.take_pct else [0.0]
        for w in windows:
            for sp in stops:
                for tp in takes:
                    out.append({"window": w, "stop_pct": sp, "take_pct": tp})
        return out

    if strat == "ema_cross":
        fasts = parse_list(args.fast, int)
        slows = parse_list(args.slow, int)
        stops = parse_list(args.stop_pct, float) if args.stop_pct else [0.0]
        takes = parse_list(args.take_pct, float) if args.take_pct else [0.0]
        for f in fasts:
            for s in slows:
                if f >= s:
                    continue
                for sp in stops:
                    for tp in takes:
                        out.append({"fast": f, "slow": s, "stop_pct": sp, "take_pct": tp})
        return out

    raise RuntimeError(f"Unknown strategy={strategy}")


# -------------------------
# Walk-forward select
# -------------------------
import json
import os
import argparse
from typing import Dict, Any, List
import pandas as pd

def calc_select_score(metrics: Dict[str, Any], metric: str) -> float:
    """Русский коммент: единая функция выбора лучшего параметра на train-части WF."""
    metric = (metric or "score").strip().lower()
    net = float(metrics.get("net_pnl", 0.0) or 0.0)
    dd = float(metrics.get("max_dd", 0.0) or 0.0)
    pf = float(metrics.get("profit_factor", 0.0) or 0.0)
    sharpe = float(metrics.get("sharpe", 0.0) or 0.0)

    if metric == "net":
        return net
    if metric == "pf":
        return pf
    if metric == "sharpe":
        return sharpe
    if metric == "dd":
        return dd
    return net / (1.0 + abs(dd))


def walk_forward_select(
    df: pd.DataFrame,
    *,
    args: argparse.Namespace,
    grid: List[Dict[str, Any]],
) -> None:
    """Русский коммент: walk-forward select — на train выбираем лучший params, на test проверяем out-of-sample."""
    splits = int(os.getenv("WF_SPLITS") or "8")
    select_metric = os.getenv("WF_SELECT_METRIC") or "score"
    if splits <= 1:
        raise RuntimeError("WF_SPLITS must be > 1")

    n = len(df)
    fold_size = n // splits
    if fold_size <= 10:
        raise RuntimeError(f"Too few rows for WF: rows={n}, splits={splits}")

    print(f"WALK-FORWARD ENABLED: mode=select splits={splits} select_metric={select_metric}")
    print(f"DB={args.db}")
    print(f"DATA symbol={args.symbol} tf={args.timeframe} rows={len(df)} range={df['ts'].min().isoformat()}..{df['ts'].max().isoformat()}")
    print(f"STRATEGY={args.strategy} grid={len(grid)} save_trades={args.save_trades}")

    test_nets: List[float] = []
    test_dds: List[float] = []
    test_pfs: List[float] = []
    test_sharpes: List[float] = []
    total_trades = 0
    selected_params_json: List[str] = []

    for split_idx in range(splits):
        test_start = split_idx * fold_size
        test_end = (split_idx + 1) * fold_size if split_idx < splits - 1 else n

        # Русский коммент: expanding/rolling-подобная схема без заглядывания в test.
        # Для первого сплита train берём весь участок до test_start; если он пустой — используем предыдущий fold как train через сдвиг.
        train_start = 0
        train_end = test_start
        if train_end <= train_start:
            continue

        train_df = df.iloc[train_start:train_end].reset_index(drop=True)
        test_df = df.iloc[test_start:test_end].reset_index(drop=True)
        if train_df.empty or test_df.empty:
            continue

        best_score = -float("inf")
        best_params = None
        best_train_metrics = None

        for pset in grid:
            train_params = dict(pset)
            train_params["timeframe"] = args.timeframe
            metrics, _ = run_backtest(
                train_df,
                strategy=args.strategy,
                params=train_params,
                starting_cash=args.starting_cash,
                qty=args.qty,
                commission_per_trade=args.commission,
                slippage_bps=args.slippage_bps,
                allow_short=args.allow_short,
            )
            score = calc_select_score(metrics, select_metric)
            if score > best_score:
                best_score = score
                best_params = train_params
                best_train_metrics = metrics

        if best_params is None or best_train_metrics is None:
            continue

        test_metrics, _ = run_backtest(
            test_df,
            strategy=args.strategy,
            params=best_params,
            starting_cash=args.starting_cash,
            qty=args.qty,
            commission_per_trade=args.commission,
            slippage_bps=args.slippage_bps,
            allow_short=args.allow_short,
        )

        test_net = float(test_metrics["net_pnl"])
        test_dd = float(test_metrics["max_dd"])
        test_trades = int(test_metrics["trades"])
        test_pf = float(test_metrics["profit_factor"])
        test_sharpe = float(test_metrics["sharpe"])

        test_nets.append(test_net)
        test_dds.append(test_dd)
        test_pfs.append(test_pf)
        test_sharpes.append(test_sharpe)
        total_trades += test_trades
        selected_params_json.append(json.dumps(best_params, ensure_ascii=False, sort_keys=True))

        print(
            f"[WF_SELECT {len(test_nets)}/{splits}] "
            f"train={train_df['ts'].min().isoformat()}..{train_df['ts'].max().isoformat()} "
            f"test={test_df['ts'].min().isoformat()}..{test_df['ts'].max().isoformat()} "
            f"train_score={best_score:.6g} train_net={float(best_train_metrics['net_pnl']):.2f} "
            f"test_net={test_net:.2f} test_dd={test_dd:.2f} test_trades={test_trades} "
            f"params={best_params}"
        )

    if not test_nets:
        print("WF_SELECT_SUMMARY splits=0 positive_splits=0/0 total_net=0 avg_net=0 min_net=0 max_net=0 avg_dd=0 worst_dd=0 avg_pf=0 avg_sharpe=0 total_trades=0 unique_param_sets=0 select_metric={}".format(select_metric))
        return

    positive = sum(1 for x in test_nets if x > 0)
    total_net = sum(test_nets)
    avg_net = total_net / len(test_nets)
    min_net = min(test_nets)
    max_net = max(test_nets)
    avg_dd = sum(test_dds) / len(test_dds)
    worst_dd = min(test_dds)
    avg_pf = sum(test_pfs) / len(test_pfs)
    avg_sharpe = sum(test_sharpes) / len(test_sharpes)
    unique_param_sets = len(set(selected_params_json))

    print(
        f"WF_SELECT_SUMMARY splits={len(test_nets)} positive_splits={positive}/{len(test_nets)} "
        f"total_net={total_net:.2f} avg_net={avg_net:.2f} min_net={min_net:.2f} max_net={max_net:.2f} "
        f"avg_dd={avg_dd:.2f} worst_dd={worst_dd:.2f} avg_pf={avg_pf:.2f} avg_sharpe={avg_sharpe:.2f} "
        f"total_trades={total_trades} unique_param_sets={unique_param_sets} select_metric={select_metric}"
    )


# -------------------------
# Persist
# -------------------------
def save_run(
    con: sqlite3.Connection,
    *,
    symbol: str,
    timeframe: str,
    strategy: str,
    params: Dict[str, Any],
    start_ts: str,
    end_ts: str,
    metrics: Dict[str, Any],
    trades: List[Trade],
    save_trades: bool,
) -> str:
    run_id = str(uuid.uuid4())
    ts_run = datetime.now(timezone.utc).isoformat()

    con.execute(
        """
        INSERT INTO backtest_runs(
            run_id, ts_run, symbol, timeframe, strategy, params_json, start_ts, end_ts,
            net_pnl, gross_pnl, max_dd, max_dd_pct,
            trades, wins, win_rate, profit_factor,
            exposure_pct, sharpe
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id, ts_run, symbol, timeframe, strategy,
            json.dumps(params, ensure_ascii=False, sort_keys=True),
            start_ts, end_ts,
            float(metrics["net_pnl"]), float(metrics["gross_pnl"]),
            float(metrics["max_dd"]), float(metrics["max_dd_pct"]),
            int(metrics["trades"]), int(metrics["wins"]),
            float(metrics["win_rate"]), float(metrics["profit_factor"]),
            float(metrics["exposure_pct"]), float(metrics["sharpe"]),
        ),
    )

    if save_trades and trades:
        for tr in trades:
            con.execute(
                """
                INSERT INTO backtest_trades(
                    trade_id, run_id, symbol, timeframe, side, qty,
                    entry_ts, entry_price, exit_ts, exit_price,
                    pnl_gross, pnl_net, commission, slippage
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()), run_id, symbol, timeframe, tr.side, float(tr.qty),
                    tr.entry_ts.isoformat(), float(tr.entry_price),
                    tr.exit_ts.isoformat(), float(tr.exit_price),
                    float(tr.pnl_gross), float(tr.pnl_net),
                    float(tr.commission), float(tr.slippage),
                ),
            )

    con.commit()
    return run_id




# -------------------------
# Reports
# -------------------------
def report_b4(con: sqlite3.Connection, *, symbol: str, timeframe: str, top: int, order: str, min_trades: int) -> None:
    """
    B4: "последний прогон каждой конфигурации" без дублей.
    Конфигурация = (symbol, timeframe, strategy, params_json)
    Правило выбора "последнего": max(ts_run), а при равенстве ts_run — max(run_id).
    """

    order = (order or "score").strip().lower()
    top = int(top or 20)
    if top <= 0:
        top = 20

    # Русский коммент: max_dd в таблице отрицательный; "лучше" — ближе к 0, т.е. max(max_dd).
    order_map = {
        "score": "score DESC",
        "net": "net_pnl DESC",
        "dd": "max_dd DESC",
        "pf": "profit_factor DESC",
        "sharpe": "sharpe DESC",
        "ts": "ts_run DESC, run_id DESC",
    }
    order_by = order_map.get(order, order_map["score"])

    sql = f"""
    WITH ranked AS (
      SELECT
        r.*,
        (r.net_pnl / (1.0 + ABS(r.max_dd))) AS score,
        ROW_NUMBER() OVER (
          PARTITION BY r.symbol, r.timeframe, r.strategy, r.params_json
          ORDER BY r.ts_run DESC, r.run_id DESC
        ) AS rn
      FROM backtest_runs r
      WHERE r.symbol=? AND r.timeframe=?
    )
    SELECT
      ts_run,
      strategy,
      net_pnl,
      max_dd,
      trades,
      win_rate,
      profit_factor,
      sharpe,
      score,
      params_json
    FROM ranked
    WHERE rn=1 AND trades >= ?
    ORDER BY {order_by}
    LIMIT ?;
    """

    cur = con.cursor()
    rows = cur.execute(sql, (symbol, timeframe, int(min_trades), int(top))).fetchall()

    print(f"B4 last-run-per-config (symbol={symbol} tf={timeframe}) top={top} order={order} min_trades={int(min_trades)}")
    if not rows:
        print("NO ROWS")
        return

    hdr = ["ts_run", "strategy", "net", "dd", "trades", "win", "pf", "sharpe", "score", "params_json"]
    print(" | ".join(hdr))
    for (ts_run, strategy, net, dd, trades, win_rate, pf, sharpe, score, params_json) in rows:
        print(
            f"{ts_run} | {strategy} | {float(net):.6g} | {float(dd):.6g} | {int(trades)} | "
            f"{float(win_rate):.4f} | {float(pf):.6g} | {float(sharpe):.6g} | {float(score):.6g} | {params_json}"
        )


# -------------------------
# CLI
# -------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.getenv("BARS_DB") or "data/bars.sqlite")
    ap.add_argument("--symbol", default=os.getenv("SYMBOL") or "NGH6@RTSX")
    ap.add_argument("--timeframe", default=(os.getenv("TIMEFRAME") or "M1").upper())
    ap.add_argument("--start", default=os.getenv("START") or "")
    ap.add_argument("--end", default=os.getenv("END") or "")
    ap.add_argument("--strategy", default=os.getenv("STRATEGY") or "vwap_bands_mr")

    ap.add_argument("--starting-cash", type=float, default=float(os.getenv("STARTING_CASH") or "100000"))
    ap.add_argument("--qty", type=float, default=float(os.getenv("QTY") or "1.0"))


    # reports
    ap.add_argument("--report", default=(os.getenv("REPORT") or "").strip())
    ap.add_argument("--top", type=int, default=int(os.getenv("TOP") or "20"))
    ap.add_argument("--order", default=(os.getenv("ORDER") or "score"))
    ap.add_argument("--min-trades", type=int, default=int(os.getenv("MIN_TRADES") or "0"))
    ap.add_argument("--commission", type=float, default=float(os.getenv("COMMISSION_PER_TRADE") or "0.0"))
    ap.add_argument("--slippage-bps", type=float, default=float(os.getenv("SLIPPAGE_BPS") or "0.0"))
    ap.add_argument("--allow-short", action="store_true", default=(os.getenv("ALLOW_SHORT", "0") == "1"))

    # grid params
    ap.add_argument("--window", default=os.getenv("WINDOW") or "200,400,800")
    ap.add_argument("--k", default=os.getenv("K") or "1.5,2.0,2.5")
    ap.add_argument("--fast", default=os.getenv("FAST") or "10,20,30")
    ap.add_argument("--slow", default=os.getenv("SLOW") or "60,90,120")
    ap.add_argument("--stop-pct", dest="stop_pct", default=os.getenv("STOP_PCT") or "0.0")
    ap.add_argument("--take-pct", dest="take_pct", default=os.getenv("TAKE_PCT") or "0.0")
    ap.add_argument("--session", default=os.getenv("SESSION") or "")
    ap.add_argument("--mr-ema", dest="mr_ema", default=os.getenv("MR_EMA") or "0")
    ap.add_argument("--mr-max-dev", dest="mr_max_dev", default=os.getenv("MR_MAX_DEV") or "0.0")
    ap.add_argument("--regime-layer", dest="regime_layer", default=os.getenv("REGIME_LAYER") or "")
    ap.add_argument("--regime-atr-n", dest="regime_atr_n", default=os.getenv("REGIME_ATR_N") or "14")
    ap.add_argument("--regime-atr-mode", dest="regime_atr_mode", default=os.getenv("REGIME_ATR_MODE") or "percentile")
    ap.add_argument("--regime-atr-threshold", dest="regime_atr_threshold", default=os.getenv("REGIME_ATR_THRESHOLD") or "0.0")
    ap.add_argument("--regime-atr-pct-window", dest="regime_atr_pct_window", default=os.getenv("REGIME_ATR_PCT_WINDOW") or "100")
    ap.add_argument("--regime-ema-slope", dest="regime_ema_slope", default=os.getenv("REGIME_EMA_SLOPE") or "")
    ap.add_argument("--regime-ema-slope-lookback", dest="regime_ema_slope_lookback", default=os.getenv("REGIME_EMA_SLOPE_LOOKBACK") or "20")
    ap.add_argument("--regime-ema-slope-threshold", dest="regime_ema_slope_threshold", default=os.getenv("REGIME_EMA_SLOPE_THRESHOLD") or "0.002")
    ap.add_argument("--daily-loss-limit", dest="daily_loss_limit", default=os.getenv("DAILY_LOSS_LIMIT") or "0.0")
    ap.add_argument("--save-trades", action="store_true", default=(os.getenv("SAVE_TRADES", "0") == "1"))
    ap.add_argument("--limit-grid", type=int, default=int(os.getenv("LIMIT_GRID") or "0"))  # 0 = без лимита

    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    ensure_results_schema(con)


    # report mode
    if args.report and args.report.strip().lower() == "b4":
        report_b4(
            con,
            symbol=args.symbol,
            timeframe=args.timeframe,
            top=args.top,
            order=args.order,
            min_trades=args.min_trades,
        )
        con.close()
        return
    # диапазон (если не задан — берём весь)
    start_ts = args.start.strip() or None
    end_ts = args.end.strip() or None

    df = load_bars(con, symbol=args.symbol, timeframe=args.timeframe, start_ts=start_ts, end_ts=end_ts)

    start_eff = df["ts"].min().isoformat()
    end_eff = df["ts"].max().isoformat()

    grid = grid_params(args.strategy, args)
    if args.limit_grid and args.limit_grid > 0:
        grid = grid[: args.limit_grid]

    print(f"DB={args.db}")
    print(f"DATA symbol={args.symbol} tf={args.timeframe} rows={len(df)} range={start_eff}..{end_eff}")
    print(f"STRATEGY={args.strategy} grid={len(grid)} save_trades={args.save_trades}")

    wf_mode = (os.getenv("WF_MODE") or "").strip().lower()
    if wf_mode == "select":
        walk_forward_select(df, args=args, grid=grid)
        con.close()
        return

    for i, pset in enumerate(grid, 1):
        # Русский коммент: протаскиваем timeframe в params для Sharpe annualization
        pset = dict(pset)
        pset["timeframe"] = args.timeframe

        metrics, trades = run_backtest(
            df,
            strategy=args.strategy,
            params=pset,
            starting_cash=args.starting_cash,
            qty=args.qty,
            commission_per_trade=args.commission,
            slippage_bps=args.slippage_bps,
            allow_short=args.allow_short,
        )
        run_id = save_run(
            con,
            symbol=args.symbol,
            timeframe=args.timeframe,
            strategy=args.strategy,
            params=pset,
            start_ts=start_eff,
            end_ts=end_eff,
            metrics=metrics,
            trades=trades,
            save_trades=args.save_trades,
        )

        print(
            f"[{i}/{len(grid)}] run_id={run_id[:8]} "
            f"net={metrics['net_pnl']:.2f} dd={metrics['max_dd']:.2f} "
            f"trades={metrics['trades']} win={metrics['win_rate']:.2%} pf={metrics['profit_factor']:.2f} sharpe={metrics['sharpe']:.2f}"
        )

    con.close()

    print("DONE. To get TOP runs:")
    print(
        "sqlite3 data/bars.sqlite \"SELECT strategy, net_pnl, max_dd, trades, win_rate, profit_factor, sharpe, params_json "
        "FROM backtest_runs WHERE symbol='{}' AND timeframe='{}' ORDER BY net_pnl DESC LIMIT 20;\"".format(
            args.symbol, args.timeframe
        )
    )
    print(
        "sqlite3 data/bars.sqlite \"SELECT strategy, net_pnl, max_dd, trades, win_rate, profit_factor, sharpe, params_json "
        "FROM backtest_runs WHERE symbol='{}' AND timeframe='{}' ORDER BY max_dd ASC LIMIT 20;\"".format(
            args.symbol, args.timeframe
        )
    )


if __name__ == "__main__":
    main()
