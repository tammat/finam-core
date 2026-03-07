#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PAPER market pipeline (Variant B: one source of truth + adapters)

Flow:
MarketData(QUOTE) -> Strategy(intent) -> Risk -> PaperExecution -> EventBus(FILL) -> PositionManager(Accounting)

Русские комментарии: каждый блок объясняет назначение и инварианты.
"""

import os
import time
import threading
from types import SimpleNamespace

from finam_core.events.event_bus import EventBus
from finam_core.adapters.grpc.market_data import FinamMarketDataClient
from finam_core.execution.paper_engine import PaperExecutionEngine

from finam_core.accounting.position_manager import PositionManager
from finam_core.accounting.portfolio_manager import PortfolioManager
from finam_core.risk.risk_engine import RiskEngine

from finam_core.core.events.fill_event import FillEvent


ACCOUNT_ID = os.getenv("FINAM_ACCOUNT_ID") or os.getenv("ACCOUNT_ID") or "1943312"


# -----------------------------
# Strategy (demo): buy once
# -----------------------------
class OnceBuyStrategy:
    """Emit a single BUY intent on first valid quote."""
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.sent = False

    def on_quote(self, state: dict):
        sym = state.get("symbol")
        last = state.get("last")

        if not self.sent:
            print(f"STRATEGY waiting first quote: {sym} last={last}", flush=True)

        if self.sent or sym != self.symbol or last is None:
            return None

        self.sent = True
        # TEST_QTY позволяет быстро проверить Risk (например 10000)
        qty = float(os.getenv("TEST_QTY", "1"))
        print("STRATEGY EMIT INTENT", flush=True)
        return {"symbol": sym, "side": "BUY", "qty": qty}


# -----------------------------
# Utils
# -----------------------------
def _safe_float(x, default=None):
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _get_price_from_state(st: dict, side: str) -> float | None:
    """Цена для оценки сделки: last -> fallback ask/bid."""
    last = st.get("last")
    bid = st.get("bid")
    ask = st.get("ask")
    px = last
    if px is None:
        px = ask if side.upper() == "BUY" else bid
    return _safe_float(px, default=None)


def _get_position_qty_from_pm(pm: PositionManager, symbol: str) -> float:
    """Best-effort qty from PositionManager positions dict."""
    try:
        pos = pm.positions.get(symbol)
        if pos is None:
            return 0.0
        return float(getattr(pos, "qty", 0.0) or 0.0)
    except Exception:
        return 0.0


def build_risk_context(intent: dict, portfolio, market_state: dict):
    """
    Контекст для RiskStack.
    Важно: starting_capital обязателен для pct-лимитов (ExposureRule/DailyLossRule и т.п.).
    """
    sym = intent.get("symbol")
    side = str(intent.get("side", "BUY")).upper()
    qty = _safe_float(intent.get("qty", intent.get("quantity", 0)) or 0.0, default=0.0)

    px = _get_price_from_state(market_state, side) or 0.0
    trade_value = abs(qty) * px

    # exposure лучше брать из PM (источник истины) если он привязан в portfolio.position_manager
    pm = getattr(portfolio, "position_manager", None)
    if pm is not None:
        total_exposure = float(getattr(pm.get_context(), "total_exposure", 0.0) or 0.0)
        pos_qty = _get_position_qty_from_pm(pm, sym)
    else:
        total_exposure = float(getattr(portfolio, "gross_exposure", 0.0) or 0.0)
        pos_qty = 0.0

    current_symbol_exposure = abs(pos_qty) * px

    # equity / starting_capital (best-effort)
    equity = getattr(portfolio, "equity", None)
    if callable(equity):
        equity = equity()
    if equity is None:
        equity = getattr(portfolio, "total_equity", None)
        equity = equity() if callable(equity) else equity
    equity = float(equity or 0.0)

    starting_capital = getattr(portfolio, "starting_cash", None)
    if starting_capital is None:
        starting_capital = getattr(portfolio, "initial_cash", None)
    if starting_capital is None:
        starting_capital = getattr(portfolio, "starting_capital", None)
    starting_capital = starting_capital() if callable(starting_capital) else starting_capital
    if starting_capital is None:
        # fallback: лучше equity, чем падение
        starting_capital = equity

    daily_realized_pnl = 0.0
    if pm is not None:
        daily_realized_pnl = float(getattr(pm, "daily_realized_pnl", 0.0) or 0.0)

    # portfolio_heat пока 0.0 (ATR нет), но поле нужно rules
    portfolio_heat = float(getattr(portfolio, "portfolio_heat", 0.0) or 0.0)

    return SimpleNamespace(
        symbol=sym,
        side=side,
        qty=float(qty),
        price=float(px),

        trade_value=float(trade_value),
        total_exposure=float(total_exposure),
        current_symbol_exposure=float(current_symbol_exposure),

        equity=float(equity),
        starting_capital=float(starting_capital),
        starting_cash=float(starting_capital),

        daily_realized_pnl=float(daily_realized_pnl),
        portfolio_heat=float(portfolio_heat),

        intent=intent,
        market_state=market_state,
        portfolio=portfolio,
    )


# -----------------------------
# Pipeline (Variant B)
# -----------------------------
class PaperTradingPipeline:
    """MarketData → Strategy → Risk → PaperExecution → EventBus(FILL) → PositionManager"""

    def __init__(self, bus, portfolio, position_manager, risk, paper, strategy, done_evt: threading.Event | None = None):
        self.bus = bus
        self.portfolio = portfolio
        self.pm = position_manager  # источник истины для учёта
        self.risk = risk
        self.paper = paper
        self.strategy = strategy
        self._done = done_evt

        self._mkt: dict[str, dict] = {}
        self._filled_once = False

        # throttle логов QUOTE
        self._last_quote_log_ts = 0.0
        self._quote_log_every = float(os.getenv("QUOTE_LOG_EVERY", "1.0"))

    def attach(self):
        # Котировки
        self.bus.subscribe("QUOTE", self._on_quote)
        # Исполнения (PaperExecution -> Accounting)
        self.bus.subscribe("FILL", self._on_fill)
        print("PIPE attach(): subscribed QUOTE -> _on_quote", flush=True)

    def _on_quote(self, event: dict):
        sym = event.get("symbol")
        if not sym:
            return

        # quote logging throttled
        now = time.time()
        last = event.get("last")
        if self._quote_log_every > 0 and (now - self._last_quote_log_ts) >= self._quote_log_every:
            self._last_quote_log_ts = now
            print(f"QUOTE {sym} last={last}", flush=True)

        # merge quote state
        st = self._mkt.get(sym, {})
        st.update(event)
        self._mkt[sym] = st

        # mark-to-market в PortfolioManager (опционально)
        last = st.get("last")
        if last is not None and hasattr(self.portfolio, "mark_price"):
            try:
                self.portfolio.mark_price(sym, float(last))
            except Exception:
                pass

        # strategy -> intent
        intent = self.strategy.on_quote(st)
        if not intent:
            return
        print(f"PIPE intent={intent}", flush=True)

        # risk (single path)
        approved = True
        decision = None

        if os.getenv("RISK_SOFT") == "1":
            print("RISK SOFT: bypass", flush=True)
        else:
            ctx = build_risk_context(intent, self.portfolio, st)
            if hasattr(self.risk, "stack") and hasattr(self.risk.stack, "evaluate"):
                decision = self.risk.stack.evaluate(ctx)
            else:
                decision = self.risk.evaluate(ctx)

            print(f"RISK decision={decision}", flush=True)

            if isinstance(decision, bool):
                approved = decision
            elif decision is None:
                approved = False
            else:
                approved = None
                for flag in ("allowed", "is_allowed", "ok", "approved", "pass_"):
                    if hasattr(decision, flag):
                        approved = bool(getattr(decision, flag))
                        break
                if approved is None:
                    approved = bool(decision)

        if not approved:
            if decision is not None:
                for attr in ("reasons", "reason", "message", "messages", "violations", "rule", "rule_name", "code"):
                    if hasattr(decision, attr):
                        print(f"RISK detail {attr}={getattr(decision, attr)}", flush=True)
            print("RISK REJECT", flush=True)
            return

        print("RISK OK", flush=True)

        # paper execution -> PaperFill
        print("PIPE PAPER EXECUTE", flush=True)
        fill = self.paper.execute(intent, st)

        # Нормализуем в FillEvent (единый формат)
        side = str(intent.get("side", "BUY")).upper()
        qty = abs(_safe_float(getattr(fill, "qty", 0.0), default=0.0) or 0.0)

        fill_event = FillEvent(
            fill_id=getattr(fill, "fill_id", None),
            symbol=getattr(fill, "symbol", None) or intent.get("symbol"),
            side=side,
            qty=qty,  # qty положительный, направление задаёт side
            price=float(getattr(fill, "price", 0.0) or 0.0),
            commission=float(getattr(fill, "commission", 0.0) or 0.0),
        )

        print(
            f"PIPE fill={fill} -> FillEvent(side={fill_event.side}, qty={fill_event.qty}, fill_id={fill_event.fill_id})",
            flush=True,
        )

        # Вариант B: исполняющий слой НЕ трогает PM напрямую, а публикует событие FILL
        self.bus.publish({"type": "FILL", "fill": fill_event, "origin": "paper"})

    def _on_fill(self, event: dict):
        """
        Единая точка учёта: только здесь обновляется PositionManager.
        """
        fill = event.get("fill") if isinstance(event, dict) else event
        if fill is None:
            return

        # apply_fill принимает fill-объект (FillEvent совместим)
        self.pm.apply_fill(fill)

        # DIAG: единый безопасный блок
        try:
            pm_ctx = self.pm.get_context()
            pos = self.pm.positions.get(getattr(fill, "symbol", None))
            qty_now = float(getattr(pos, "qty", 0.0) or 0.0) if pos is not None else 0.0
            avg_now = float(getattr(pos, "avg_price", 0.0) or 0.0) if pos is not None else 0.0
            cash_now = float(getattr(self.pm, "cash", 0.0) or 0.0)
            sym_exposure = abs(qty_now) * float(getattr(fill, "price", 0.0) or 0.0)

            print(
                "PM_CTX "
                f"portfolio_value={getattr(pm_ctx, 'portfolio_value', None)} "
                f"total_exposure={getattr(pm_ctx, 'total_exposure', None)} "
                f"sym_exposure={sym_exposure} "
                f"daily_realized_pnl={getattr(pm_ctx, 'daily_realized_pnl', None)} "
                f"qty={qty_now} avg={avg_now} cash={cash_now}",
                flush=True,
            )
        except Exception as e:
            print(f"PM_CTX DIAG ERROR: {e}", flush=True)

        print(
            f"FILLED paper {getattr(fill, 'symbol', None)} qty={getattr(fill, 'qty', None)} "
            f"price={getattr(fill, 'price', None)} id={getattr(fill, 'fill_id', None)}",
            flush=True,
        )

        # exit-on-fill: default EXIT_ON_FILL=1
        if not self._filled_once and os.getenv("EXIT_ON_FILL", "1") == "1":
            self._filled_once = True
            print("DONE: filled once, exiting", flush=True)
            if self._done is not None:
                self._done.set()


def main():
    os.environ.setdefault("EXECUTION_MODE", "paper")

    symbol = os.getenv("SYMBOL") or "GAZP@MISX"
    run_secs = float(os.getenv("RUN_SECS") or "0")
    starting_cash = float(os.getenv("STARTING_CASH") or "100000")
    md_hb = float(os.getenv("MD_HEARTBEAT_SEC") or "10")

    print(f"Starting PAPER market pipeline. account={ACCOUNT_ID} symbol={symbol}", flush=True)

    bus = EventBus()
    done = threading.Event()

    # PositionManager = источник истины (учёт)
    pm = PositionManager(starting_cash=starting_cash)
    pm.cash = starting_cash
    pm.starting_cash = starting_cash
    pm.starting_capital = starting_cash

    # PortfolioManager оставляем как “витрину” для risk/mark_price; привязываем тот же pm
    try:
        portfolio = PortfolioManager(starting_cash=starting_cash)
    except TypeError:
        try:
            portfolio = PortfolioManager(initial_cash=starting_cash)
        except TypeError:
            portfolio = PortfolioManager(starting_cash)

    setattr(portfolio, "position_manager", pm)
    setattr(portfolio, "starting_cash", starting_cash)
    setattr(portfolio, "starting_capital", starting_cash)

    risk = RiskEngine()
    paper = PaperExecutionEngine(slippage_coef=0.25, commission=0.0)
    strategy = OnceBuyStrategy(symbol)

    pipeline = PaperTradingPipeline(bus, portfolio, pm, risk, paper, strategy, done)
    pipeline.attach()

    # MarketData: поддержка разных версий сигнатуры
    try:
        md = FinamMarketDataClient(bus, heartbeat_sec=md_hb)
    except TypeError:
        try:
            md = FinamMarketDataClient(bus, heartbeat=md_hb)
        except TypeError:
            md = FinamMarketDataClient(bus)
            # last resort: установим поле вручную
            if hasattr(md, "heartbeat_sec"):
                md.heartbeat_sec = md_hb
            elif hasattr(md, "heartbeat"):
                md.heartbeat = md_hb

    print("Starting MD...", flush=True)
    md.start([symbol])

    deadline = time.time() + run_secs if run_secs and run_secs > 0 else None
    try:
        while True:
            if done.wait(timeout=0.5):
                return
            if deadline is not None and time.time() >= deadline:
                print("RUN_SECS reached, exit", flush=True)
                return
    finally:
        # safe stop
        try:
            if hasattr(md, "stop") and callable(getattr(md, "stop")):
                md.stop()
        except Exception:
            pass
        print("DONE", flush=True)


if __name__ == "__main__":
    main()
