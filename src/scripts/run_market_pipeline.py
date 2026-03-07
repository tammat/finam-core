# src/scripts/run_market_pipeline.py
# --------------------------------------------------------------------
# Вариант B: один источник истины (PositionManager) + адаптеры событий
#
# Поток:
#   MarketData(QUOTE) -> Strategy(intent) -> Risk -> PaperExecution(fill)
#   -> EventBus.publish({"type":"FILL","fill": FillEvent(...)})
#   -> Accounting(PositionManager.apply_fill)  [ТОЛЬКО в _on_fill]
#
# Ключевое:
# - В _on_quote НЕТ self.pm.apply_fill (никаких double-apply).
# - EventBus у тебя: subscribe(event_type, handler) + publish(event)
#   => publish принимает ОДИН аргумент: dict с event["type"].
# --------------------------------------------------------------------

import os
import time
import threading

from finam_core.events.event_bus import EventBus
from finam_core.adapters.grpc.market_data import FinamMarketDataClient
from finam_core.execution.paper_engine import PaperExecutionEngine

from finam_core.accounting.position_manager import PositionManager
from finam_core.accounting.portfolio_manager import PortfolioManager
from finam_core.risk.risk_engine import RiskEngine

# Единый формат исполнения для accounting (PositionManager.apply_fill ожидает fill.side и fill.qty>0)
from finam_core.core.events.fill_event import FillEvent


ACCOUNT_ID = os.getenv("FINAM_ACCOUNT_ID") or os.getenv("ACCOUNT_ID") or "1943312"


# -------------------------
# Strategy
# -------------------------
class OnceBuyStrategy:
    """Отправляет один BUY intent по первому валидному last."""

    def __init__(self, symbol: str, qty: float = 1.0):
        self.symbol = symbol
        self.qty = float(qty)
        self.sent = False

    def on_quote(self, state: dict):
        sym = state.get("symbol")
        last = state.get("last")

        if not self.sent:
            print(f"STRATEGY waiting first quote: {sym} last={last}", flush=True)

        if self.sent or sym != self.symbol or last is None:
            return None

        self.sent = True
        print("STRATEGY EMIT INTENT", flush=True)
        return {"symbol": sym, "side": "BUY", "qty": float(self.qty)}


# -------------------------
# Helpers
# -------------------------
def _safe_float(x, default=None):
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _get_price_from_state(st: dict, side: str) -> float | None:
    last = st.get("last")
    bid = st.get("bid")
    ask = st.get("ask")

    px = last
    if px is None:
        px = ask if side.upper() == "BUY" else bid
    return _safe_float(px, default=None)


def build_risk_context(intent: dict, portfolio, market_state: dict):
    """
    Контекст для RiskStack.
    Важно: exposure / pnl берём от PositionManager (как источника истины),
    который у нас привязан к portfolio.position_manager.
    """
    from types import SimpleNamespace

    sym = intent.get("symbol")
    side = str(intent.get("side", "BUY")).upper()
    qty = _safe_float(intent.get("qty", intent.get("quantity", 0)) or 0.0, default=0.0)

    px = _get_price_from_state(market_state, side) or 0.0
    trade_value = abs(qty) * px

    pm = getattr(portfolio, "position_manager", None)

    # starting_capital / equity — best effort
    starting_capital = getattr(portfolio, "starting_cash", None)
    if starting_capital is None:
        starting_capital = getattr(portfolio, "initial_cash", None)
    if starting_capital is None:
        starting_capital = getattr(pm, "starting_cash", None)
    if starting_capital is None:
        starting_capital = getattr(pm, "starting_capital", None)
    starting_capital = float(starting_capital) if starting_capital is not None else 0.0

    equity = getattr(portfolio, "equity", None)
    if callable(equity):
        equity = equity()
    if equity is None and pm is not None and hasattr(pm, "total_equity"):
        try:
            equity = float(pm.total_equity())
        except Exception:
            equity = None
    if equity is None:
        equity = float(starting_capital)

    # exposures / pnl — из pm.get_context() если доступно
    total_exposure = 0.0
    daily_realized_pnl = 0.0
    portfolio_heat = 0.0
    if pm is not None and hasattr(pm, "get_context"):
        try:
            pm_ctx = pm.get_context()
            total_exposure = float(getattr(pm_ctx, "total_exposure", 0.0) or 0.0)
            daily_realized_pnl = float(getattr(pm_ctx, "daily_realized_pnl", 0.0) or 0.0)
            portfolio_heat = float(getattr(pm_ctx, "portfolio_heat", 0.0) or 0.0)
        except Exception:
            pass

    # текущая экспозиция по символу — напрямую из pm.positions
    current_symbol_exposure = 0.0
    if pm is not None and hasattr(pm, "positions"):
        try:
            pos = pm.positions.get(sym)
            pos_qty = float(getattr(pos, "qty", 0.0) or 0.0) if pos is not None else 0.0
            current_symbol_exposure = abs(pos_qty) * float(px)
        except Exception:
            current_symbol_exposure = 0.0

    # daily_pnl: если нет явного поля, держим 0 (не роняем пайплайн)
    daily_pnl = getattr(portfolio, "daily_pnl", 0.0)
    if daily_pnl is None:
        daily_pnl = 0.0

    return SimpleNamespace(
        symbol=sym,
        side=side,
        qty=float(qty),
        price=float(px),

        trade_value=float(trade_value),
        total_exposure=float(total_exposure),
        current_symbol_exposure=float(current_symbol_exposure),

        daily_pnl=float(daily_pnl),
        daily_realized_pnl=float(daily_realized_pnl),
        portfolio_heat=float(portfolio_heat),

        equity=float(equity),
        starting_capital=float(starting_capital),
        starting_cash=float(starting_capital),

        intent=intent,
        market_state=market_state,
        portfolio=portfolio,
    )


# -------------------------
# Pipeline (B)
# -------------------------
class PaperTradingPipeline:
    """MarketData -> Strategy -> Risk -> PaperExecution -> (publish FILL) -> Accounting"""

    def __init__(self, bus, portfolio, position_manager, risk, paper, strategy, done_event: threading.Event | None):
        self.bus = bus
        self.portfolio = portfolio
        self.pm = position_manager  # источник истины для учёта
        self.risk = risk
        self.paper = paper
        self.strategy = strategy
        self._done = done_event

        self._mkt = {}
        self._filled_once = False

        self._last_quote_log_ts = 0.0
        self._quote_log_every = float(os.getenv("QUOTE_LOG_EVERY", "0"))  # 0 = без лог-троттлинга

    def attach(self):
        # ВАЖНО (B): QUOTE -> _on_quote, FILL -> _on_fill
        self.bus.subscribe("QUOTE", self._on_quote)
        self.bus.subscribe("FILL", self._on_fill)
        print("PIPE attach(): subscribed QUOTE -> _on_quote", flush=True)

    def _on_quote(self, event: dict):
        sym = event.get("symbol")
        if not sym:
            return

        # троттлинг лога котировок
        now = time.time()
        last_ev = event.get("last")
        if self._quote_log_every > 0 and (now - self._last_quote_log_ts) >= self._quote_log_every:
            self._last_quote_log_ts = now
            print(f"QUOTE {sym} last={last_ev}", flush=True)

        # merge состояния рынка
        st = self._mkt.get(sym, {})
        st.update(event)
        self._mkt[sym] = st

        # mark-to-market (если PortfolioManager умеет)
        last = st.get("last")
        if last is not None and hasattr(self.portfolio, "mark_price"):
            try:
                self.portfolio.mark_price(sym, float(last))
            except Exception:
                pass

        # strategy
        intent = self.strategy.on_quote(st)
        if not intent:
            return
        print(f"PIPE intent={intent}", flush=True)

        # risk (один путь, без double-eval)
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

        # paper execution -> публикуем FILL (B)
        print("PIPE PAPER EXECUTE", flush=True)
        fill = self.paper.execute(intent, st)

        side = str(intent.get("side", "BUY")).upper()
        qty = abs(_safe_float(getattr(fill, "qty", 0.0), default=0.0) or 0.0)

        pm_fill = FillEvent(
            fill_id=getattr(fill, "fill_id", None),
            symbol=getattr(fill, "symbol", None) or intent.get("symbol"),
            side=side,
            qty=qty,  # qty положительный, side задаёт направление
            price=float(getattr(fill, "price", 0.0) or 0.0),
            commission=float(getattr(fill, "commission", 0.0) or 0.0),
        )

        print(
            f"PIPE fill={fill} -> FillEvent(side={pm_fill.side}, qty={pm_fill.qty}, fill_id={pm_fill.fill_id})",
            flush=True,
        )

        # ВАЖНО: publish(event) — один аргумент, event["type"]="FILL"
        self.bus.publish({"type": "FILL", "fill": pm_fill, "origin": "paper"})

    def _on_fill(self, event: dict):
        """Accounting handler: единственное место, где вызываем pm.apply_fill()."""
        fill = event.get("fill")
        if fill is None:
            return

        # ЕДИНЫЙ учёт исполнений
        self.pm.apply_fill(fill)

        # DIAG (безопасно, единым блоком)
        try:
            pm_ctx = self.pm.get_context()
            pos = self.pm.positions.get(fill.symbol)
            qty_now = float(getattr(pos, "qty", 0.0) or 0.0) if pos is not None else 0.0
            avg_now = float(getattr(pos, "avg_price", 0.0) or 0.0) if pos is not None else 0.0
            cash_now = float(getattr(self.pm, "cash", 0.0) or 0.0)
            sym_exposure = abs(qty_now) * float(fill.price)

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
            f"FILLED paper {fill.symbol} qty={fill.qty} price={fill.price} id={fill.fill_id}",
            flush=True,
        )

        # EXIT_ON_FILL: по умолчанию 1 (выход после первого fill), EXIT_ON_FILL=0 -> остаёмся
        if not self._filled_once and os.getenv("EXIT_ON_FILL", "1") == "1":
            self._filled_once = True
            print("DONE: filled once, exiting", flush=True)
            if self._done is not None:
                self._done.set()
            return


# -------------------------
# main
# -------------------------
def main():
    os.environ.setdefault("EXECUTION_MODE", "paper")

    symbol = os.getenv("SYMBOL") or "GAZP@MISX"
    run_secs = float(os.getenv("RUN_SECS") or "0")
    starting_cash = float(os.getenv("STARTING_CASH") or "100000")
    md_hb = float(os.getenv("MD_HEARTBEAT_SEC") or "10")
    test_qty = float(os.getenv("TEST_QTY") or "1")

    print(f"Starting PAPER market pipeline. account={ACCOUNT_ID} symbol={symbol}", flush=True)

    bus = EventBus()
    done = threading.Event()

    # PositionManager = source-of-truth для paper accounting
    pm = PositionManager(starting_cash=starting_cash)
    # эти поля часто ожидают risk rules
    pm.cash = starting_cash
    pm.starting_cash = starting_cash
    pm.starting_capital = starting_cash

    # PortfolioManager оставляем для mark_price + контекста (привязываем pm)
    try:
        portfolio = PortfolioManager(starting_cash=starting_cash)
    except TypeError:
        try:
            portfolio = PortfolioManager(initial_cash=starting_cash)
        except TypeError:
            portfolio = PortfolioManager(starting_cash)
    setattr(portfolio, "position_manager", pm)

    risk = RiskEngine()
    paper = PaperExecutionEngine(slippage_coef=0.25, commission=0.0)
    strategy = OnceBuyStrategy(symbol, qty=test_qty)

    pipeline = PaperTradingPipeline(bus, portfolio, pm, risk, paper, strategy, done)
    pipeline.attach()

    # MarketData client: поддержка разных сигнатур __init__
    try:
        md = FinamMarketDataClient(bus, heartbeat_sec=md_hb)
    except TypeError:
        try:
            md = FinamMarketDataClient(bus, heartbeat=md_hb)
        except TypeError:
            md = FinamMarketDataClient(bus)
            # last resort: выставим атрибут, если он существует
            if hasattr(md, "heartbeat_sec"):
                md.heartbeat_sec = float(md_hb)

    print("Starting MD...", flush=True)
    md.start([symbol])

    deadline = time.time() + run_secs if run_secs and run_secs > 0 else None
    try:
        while True:
            # выход по done (если EXIT_ON_FILL=1)
            if done.wait(timeout=0.5):
                return
            # выход по RUN_SECS
            if deadline is not None and time.time() >= deadline:
                print("RUN_SECS reached, exit", flush=True)
                return
    finally:
        # аккуратное завершение (разные версии клиента)
        try:
            if hasattr(md, "stop") and callable(getattr(md, "stop")):
                md.stop()
            elif hasattr(md, "_stop"):
                try:
                    md._stop.set()
                except Exception:
                    pass
        except Exception:
            pass
        print("DONE", flush=True)


if __name__ == "__main__":
    main()