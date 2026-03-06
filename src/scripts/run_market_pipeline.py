import time
import os
import threading
from types import SimpleNamespace
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass
import time
import threading

from finam_core.events.event_bus import EventBus
from finam_core.adapters.grpc.market_data import FinamMarketDataClient
from finam_core.execution.paper_engine import PaperExecutionEngine

from finam_core.accounting.position_manager import PositionManager
from finam_core.accounting.portfolio_manager import PortfolioManager
from finam_core.risk.risk_engine import RiskEngine


ACCOUNT_ID = os.getenv("FINAM_ACCOUNT_ID") or os.getenv("ACCOUNT_ID") or "1943312"


class OnceBuyStrategy:
    """Emit a single BUY intent on first valid quote."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.sent = False
        self.test_qty = float(os.getenv("TEST_QTY", "1") or "1")

    def on_quote(self, state: dict):
        sym = state.get("symbol")
        last = state.get("last")

        if not self.sent:
            print(f"STRATEGY waiting first quote: {sym} last={last}", flush=True)

        if self.sent or sym != self.symbol or last is None:
            return None

        self.sent = True
        print("STRATEGY EMIT INTENT", flush=True)
        return {"symbol": sym, "side": "BUY", "qty": self.test_qty}


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


def _get_position_qty_from_pm(pm: PositionManager, symbol: str) -> float:
    try:
        pos = pm.positions.get(symbol)
        if pos is None:
            return 0.0
        return float(getattr(pos, "qty", 0.0) or 0.0)
    except Exception:
        return 0.0



def build_risk_context(intent: dict, portfolio, market_state: dict):
    """Context builder for RiskStack rules.
    Source of truth: PositionManager (portfolio.position_manager), portfolio is fallback.
    """
    sym = intent.get("symbol")
    side = str(intent.get("side", "BUY")).upper()
    qty = _safe_float(intent.get("qty", intent.get("quantity", 0)) or 0.0, default=0.0)

    px = _get_price_from_state(market_state, side) or 0.0
    trade_value = abs(qty) * px

    # -------- source of truth --------
    pm = getattr(portfolio, "position_manager", None)

    # equity / starting_capital
    equity = None
    starting_capital = None
    daily_realized_pnl = None
    total_exposure = None
    portfolio_heat = None
    daily_pnl = getattr(portfolio, "daily_pnl", 0.0)  # optional / informational

    # Prefer PM if present
    if pm is not None:
        # equity
        if hasattr(pm, "total_equity") and callable(pm.total_equity):
            try:
                equity = pm.total_equity()
            except Exception:
                equity = None
        if equity is None:
            equity = getattr(pm, "equity", None)
            if callable(equity):
                try:
                    equity = equity()
                except Exception:
                    equity = None

        # starting capital
        starting_capital = getattr(pm, "starting_cash", None)
        if starting_capital is None:
            starting_capital = getattr(pm, "starting_capital", None)
        if callable(starting_capital):
            try:
                starting_capital = starting_capital()
            except Exception:
                starting_capital = None

        # realized pnl (daily)
        daily_realized_pnl = getattr(pm, "daily_realized_pnl", None)
        if daily_realized_pnl is None:
            daily_realized_pnl = 0.0

        # exposure from PM.get_context() if available
        if hasattr(pm, "get_context") and callable(pm.get_context):
            try:
                ctx_pm = pm.get_context()
                total_exposure = getattr(ctx_pm, "total_exposure", None)
                portfolio_heat = getattr(ctx_pm, "portfolio_heat", None)
            except Exception:
                total_exposure = None
                portfolio_heat = None

        if total_exposure is None:
            total_exposure = 0.0
        if portfolio_heat is None:
            portfolio_heat = 0.0

    # -------- fallbacks to portfolio --------
    if equity is None:
        equity = getattr(portfolio, "equity", None)
        if callable(equity):
            equity = equity()
    if equity is None:
        equity = getattr(portfolio, "total_equity", 0.0)

    if starting_capital is None:
        starting_capital = getattr(portfolio, "starting_cash", None)
        if starting_capital is None:
            starting_capital = getattr(portfolio, "initial_cash", None)
        if starting_capital is None:
            starting_capital = getattr(portfolio, "starting_capital", None)
        if callable(starting_capital):
            starting_capital = starting_capital()
        if starting_capital is None:
            starting_capital = equity  # safe fallback

    if total_exposure is None:
        total_exposure = getattr(portfolio, "total_exposure", None)
        if total_exposure is None:
            total_exposure = getattr(portfolio, "gross_exposure", 0.0)

    if daily_realized_pnl is None:
        daily_realized_pnl = getattr(portfolio, "daily_realized_pnl", None)
        if daily_realized_pnl is None:
            daily_realized_pnl = 0.0

    if portfolio_heat is None:
        portfolio_heat = getattr(portfolio, "portfolio_heat", None)
        if portfolio_heat is None:
            portfolio_heat = 0.0

    # current symbol exposure (prefer PM positions)
    pos_qty = 0.0
    if pm is not None:
        pos_qty = _get_position_qty_from_pm(pm, sym)
    current_symbol_exposure = abs(pos_qty) * px

    return SimpleNamespace(
        symbol=sym,
        side=side,
        qty=float(qty),
        price=float(px),

        trade_value=float(trade_value),
        total_exposure=float(total_exposure) if total_exposure is not None else 0.0,
        current_symbol_exposure=float(current_symbol_exposure),
        daily_pnl=float(daily_pnl) if daily_pnl is not None else 0.0,
        daily_realized_pnl=float(daily_realized_pnl) if daily_realized_pnl is not None else 0.0,
        portfolio_heat=float(portfolio_heat) if portfolio_heat is not None else 0.0,

        equity=float(equity) if equity is not None else 0.0,
        starting_capital=float(starting_capital) if starting_capital is not None else 0.0,
        starting_cash=float(starting_capital) if starting_capital is not None else 0.0,

        intent=intent,
        market_state=market_state,
        portfolio=portfolio,
    )


class PaperTradingPipeline:
    """MarketData → Strategy → Risk → PaperExecution → PositionManager"""

    def __init__(
        self,
        bus: EventBus,
        portfolio: PortfolioManager,
        position_manager: PositionManager,
        risk: RiskEngine,
        paper: PaperExecutionEngine,
        strategy: OnceBuyStrategy,
        done: threading.Event | None = None,
    ):
        self.bus = bus
        self.portfolio = portfolio
        self.pm = position_manager
        self.risk = risk
        self.paper = paper
        self.strategy = strategy

        self._mkt: dict[str, dict] = {}
        self._filled_once = False
        self._done = done

        self._last_quote_log_ts = 0.0
        self._quote_log_every = float(os.getenv("QUOTE_LOG_EVERY", "1.0") or "1.0")

    def attach(self):
        self.bus.subscribe("QUOTE", self._on_quote)

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

        # optional mark-to-market (PortfolioManager may expose mark_price)
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

        # risk (single path)
        approved = True
        decision = None

        if os.getenv("RISK_SOFT") == "1":
            print("RISK SOFT: bypass", flush=True)
        else:
            ctx = build_risk_context(intent, self.portfolio, st)
            print(
                f"DBG equity={getattr(ctx, 'equity', None)} "
                f"start={getattr(ctx, 'starting_capital', None)} "
                f"total={getattr(ctx, 'total_exposure', None)} "
                f"sym={getattr(ctx, 'current_symbol_exposure', None)} "
                f"tv={getattr(ctx, 'trade_value', None)}",
                flush=True
            )
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

        # paper execution
        print("PIPE PAPER EXECUTE", flush=True)
        fill = self.paper.execute(intent, st)

        side = str(intent.get("side", "BUY")).upper()
        qty = abs(_safe_float(getattr(fill, "qty", 0.0), default=0.0) or 0.0)
        pm_fill = SimpleNamespace(
            symbol=getattr(fill, "symbol", None) or intent.get("symbol"),
            side=side,
            qty=qty,  # PositionManager expects positive qty; side carries direction
            price=float(getattr(fill, "price", 0.0) or 0.0),
            commission=float(getattr(fill, "commission", 0.0) or 0.0),
            fill_id=getattr(fill, "fill_id", None),
            event_id=getattr(fill, "event_id", None),
        )

        print(f"PIPE fill={fill} -> pm_fill(side={pm_fill.side}, qty={pm_fill.qty})", flush=True)

        # single source of truth: ONLY PositionManager.apply_fill
        self.pm.apply_fill(pm_fill)

        # --- DIAG: PM context after fill (safe) ---
        try:
            pm_ctx = self.pm.get_context()
            pos = self.pm.positions.get(pm_fill.symbol)
            sym_exposure = None
            if pos is not None:
                sym_exposure = abs(float(getattr(pos, "qty", 0.0) or 0.0)) * float(pm_fill.price)
            print(
                "PM_CTX "
                f"portfolio_value={getattr(pm_ctx, 'portfolio_value', None)} "
                f"total_exposure={getattr(pm_ctx, 'total_exposure', None)} "
                f"sym_exposure={sym_exposure} "
                f"daily_realized_pnl={getattr(pm_ctx, 'daily_realized_pnl', None)}",
                flush=True,
            )
        except Exception as e:
            print(f"PM_CTX DIAG ERROR: {e}", flush=True)
        # safe diag (no exceptions)
        pos = self.pm.positions.get(pm_fill.symbol)
        q = float(getattr(pos, "qty", 0.0) or 0.0) if pos is not None else 0.0
        avg = float(getattr(pos, "avg_price", 0.0) or 0.0) if pos is not None else 0.0
        cash = float(getattr(self.pm, "cash", 0.0) or 0.0)
        print(f"PM qty[{pm_fill.symbol}]={q} avg={avg} cash={cash}", flush=True)

        print(f"FILLED paper {pm_fill.symbol} qty={pm_fill.qty} price={pm_fill.price} id={pm_fill.fill_id}", flush=True)

        # exit-on-fill behavior: default EXIT_ON_FILL=1; keep streaming when 0
        if not self._filled_once and os.getenv("EXIT_ON_FILL", "1") == "1":
            self._filled_once = True
            print("DONE: filled once, exiting", flush=True)
            if self._done is not None:
                self._done.set()
            return


def main():
    os.environ.setdefault("EXECUTION_MODE", "paper")

    symbol = os.getenv("SYMBOL") or "GAZP@MISX"
    run_secs = float(os.getenv("RUN_SECS") or "0")
    starting_cash = float(os.getenv("STARTING_CASH") or "100000")
    md_hb = float(os.getenv("MD_HEARTBEAT_SEC") or "10")

    print(f"Starting PAPER market pipeline. account={ACCOUNT_ID} symbol={symbol}", flush=True)

    bus = EventBus()
    done = threading.Event()

    # PositionManager is paper accounting source-of-truth
    pm = PositionManager(starting_cash=starting_cash)
    # ensure these exist for risk rules
    pm.cash = starting_cash
    pm.starting_cash = starting_cash
    pm.starting_capital = starting_cash

    # PortfolioManager: kept for mark_price + risk context (shares pm via attribute)
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
    strategy = OnceBuyStrategy(symbol)

    pipeline = PaperTradingPipeline(bus, portfolio, pm, risk, paper, strategy, done)
    pipeline.attach()

    # MarketData client: support разных версий сигнатуры __init__
    try:
        md = FinamMarketDataClient(bus, heartbeat_sec=md_hb)
    except TypeError:
        try:
            md = FinamMarketDataClient(bus, heartbeat=md_hb)
        except TypeError:
            md = FinamMarketDataClient(bus)
            # last resort: если параметр называется иначе — просто пишем атрибут
            if hasattr(md, "heartbeat_sec"):
                md.heartbeat_sec = float(md_hb)
            elif hasattr(md, "heartbeat"):
                md.heartbeat = float(md_hb)
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
        # safe shutdown for different MarketDataClient versions
        # safe shutdown for different MarketDataClient versions (avoid channel.close() spam)
        try:
            if hasattr(md, "stop") and callable(getattr(md, "stop")):
                md.stop()
            else:
                if hasattr(md, "_stop"):
                    try:
                        md._stop.set()
                    except Exception:
                        pass
                # IMPORTANT: do NOT close channel here -> prevents CANCELLED spam
        except Exception:
            pass

        print("DONE", flush=True)

if __name__ == "__main__":
    main()
