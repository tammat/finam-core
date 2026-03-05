import os
import time
from types import SimpleNamespace

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

    def on_quote(self, state: dict):
        sym = state.get("symbol")
        last = state.get("last")
        if not self.sent:
            print(f"STRATEGY waiting first quote: {sym} last={last}", flush=True)
        if self.sent or sym != self.symbol or last is None:
            return None

        self.sent = True
        print("STRATEGY EMIT INTENT", flush=True)
        return {"symbol": sym, "side": "BUY", "qty": 1}


def _get_position_qty(portfolio, symbol: str) -> float:
    if hasattr(portfolio, "get_position_qty"):
        try:
            return float(portfolio.get_position_qty(symbol))
        except Exception:
            pass
    pm = getattr(portfolio, "position_manager", None)
    if pm is not None and hasattr(pm, "get_position_qty"):
        try:
            return float(pm.get_position_qty(symbol))
        except Exception:
            pass
    return 0.0


def build_risk_context(intent: dict, portfolio, market_state: dict):
    sym = intent.get("symbol")
    side = intent.get("side")
    qty = float(intent.get("qty", intent.get("quantity", 0)) or 0)

    last = market_state.get("last")
    bid = market_state.get("bid")
    ask = market_state.get("ask")

    px = last
    if px is None:
        px = ask if str(side).upper() == "BUY" else bid
    px = float(px) if px is not None else 0.0

    trade_value = abs(qty) * px

    total_exposure = getattr(portfolio, "total_exposure", None)
    if callable(total_exposure):
        total_exposure = total_exposure()
    if total_exposure is None:
        total_exposure = getattr(portfolio, "gross_exposure", 0.0)

    daily_pnl = getattr(portfolio, "daily_pnl", 0.0)

    equity = getattr(portfolio, "equity", None)
    if callable(equity):
        equity = equity()
    if equity is None:
        equity = getattr(portfolio, "total_equity", 0.0)

    starting_capital = getattr(portfolio, "starting_cash", None)
    if starting_capital is None:
        starting_capital = getattr(portfolio, "initial_cash", None)
    if starting_capital is None:
        starting_capital = getattr(portfolio, "starting_capital", None)
    if callable(starting_capital):
        starting_capital = starting_capital()
    if starting_capital is None:
        starting_capital = equity  # fallback лучше чем падать

    pos_qty = _get_position_qty(portfolio, sym)
    current_symbol_exposure = abs(pos_qty) * px
    # daily_realized_pnl: try PositionManager first (preferred), then portfolio fallbacks
    daily_realized_pnl = 0.0

    pm = getattr(portfolio, "position_manager", None)
    if pm is None:
        pm = getattr(portfolio, "pm", None)
    if pm is not None:
        for attr in ("daily_realized_pnl", "daily_pnl_realized", "daily_realized"):
            if hasattr(pm, attr):
                try:
                    daily_realized_pnl = float(getattr(pm, attr))
                    break
                except Exception:
                    pass

    if daily_realized_pnl == 0.0:
        for attr in ("daily_realized_pnl", "daily_pnl", "realized_pnl", "daily_realized"):
            if hasattr(portfolio, attr):
                try:
                    v = getattr(portfolio, attr)
                    daily_realized_pnl = float(v() if callable(v) else v)
                    break
                except Exception:
                    pass
    # portfolio_heat: best-effort
    # Обычно это доля экспозиции от капитала. Берём starting_capital, чтобы не делить на 0.
    denom = float(starting_capital) if starting_capital not in (None, 0, 0.0) else float(equity or 0.0)
    if denom <= 0:
        portfolio_heat = 0.0
    else:
        # текущая "теплота" портфеля
        portfolio_heat = float(total_exposure) / denom

    return SimpleNamespace(
        total_exposure=float(total_exposure) if total_exposure is not None else 0.0,
        current_symbol_exposure=float(current_symbol_exposure),
        trade_value=float(trade_value),
        daily_pnl=float(daily_pnl) if daily_pnl is not None else 0.0,
        equity=float(equity) if equity is not None else 0.0,
        starting_capital=float(starting_capital) if starting_capital is not None else 0.0,
        starting_cash=float(starting_capital) if starting_capital is not None else 0.0,
        symbol=sym,
        side=str(side).upper(),
        qty=float(qty),
        price=float(px),
        position_qty=float(pos_qty),
        intent=intent,
        market_state=market_state,
        portfolio=portfolio,
        daily_realized_pnl=float(daily_realized_pnl),
        portfolio_heat=float(portfolio_heat),
    )


class PaperTradingPipeline:
    """MarketData → Strategy → Risk → PaperExecution → Accounting"""

    def __init__(self, bus, portfolio, position_manager, risk, paper, strategy):
        self.bus = bus
        self.portfolio = portfolio
        self.pm = position_manager
        self.risk = risk
        self.paper = paper

        self.strategy = strategy
        self._mkt = {}
        self._filled_once = False

        self._last_quote_log_ts = 0.0
        self._quote_log_every = float(os.getenv("QUOTE_LOG_EVERY", "1.0"))
    def attach(self):
        self.bus.subscribe("QUOTE", self._on_quote)

    def _on_quote(self, event: dict):
        sym = event.get("symbol")
        if not sym:
            return

        # --- merge quote state ---
        st = self._mkt.get(sym, {})
        st.update(event)
        self._mkt[sym] = st
        now = time.time()
        if self._quote_log_every > 0 and (now - self._last_quote_log_ts) >= self._quote_log_every:
            print(f"QUOTE {sym} last={st.get('last')}", flush=True)
            self._last_quote_log_ts = now
        # --- push price into portfolio if it supports it ---
        last = st.get("last")
        if last is not None:
            px = float(last)
            if hasattr(self.portfolio, "on_price"):
                self.portfolio.on_price(sym, px)
            elif hasattr(self.portfolio, "update_market_price"):
                self.portfolio.update_market_price(sym, px)

        # --- strategy ---
        intent = self.strategy.on_quote(st)
        if intent:
            print(f"PIPE intent={intent}", flush=True)
        if not intent:
            return

        # --- RISK (single path) ---
        if os.getenv("RISK_SOFT") == "1":
            print("RISK SOFT: bypass", flush=True)
            approved = True
            decision = None
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

        # --- PAPER EXECUTE ---
        print("PIPE PAPER EXECUTE", flush=True)
        fill = self.paper.execute(intent, st)

        from types import SimpleNamespace

        side = str(intent.get("side", "BUY")).upper()

        # PositionManager ожидает fill.qty как МОДУЛЬ, а знак берёт из fill.side
        fill_pm = SimpleNamespace(
            symbol=fill.symbol,
            qty=abs(float(fill.qty)),
            price=float(fill.price),
            side=side,
            commission=float(getattr(fill, "commission", 0.0)),
            fill_id=getattr(fill, "fill_id", None),
            event_id=getattr(fill, "event_id", None),
        )

        print(f"PIPE fill={fill} -> pm_fill(side={fill_pm.side}, qty={fill_pm.qty})", flush=True)

        # --- APPLY FILL: ONLY via accounting PositionManager.apply_fill(fill) ---
        pm = getattr(self, "position_manager", None)
        if pm is None:
            pm = getattr(self.portfolio, "position_manager", None)

        if pm is None or not hasattr(pm, "apply_fill"):
            print("ACCOUNTING ERROR: PositionManager not wired (no pm.apply_fill)", flush=True)
            return

        pm.apply_fill(fill_pm)
        if not self._filled_once and os.getenv("EXIT_ON_FILL", "1") == "1":
            self._filled_once = True
            print("DONE: filled once, exiting", flush=True)
            os._exit(0)
        # DIAG: read qty from PM directly (source of truth)
        try:
            pos = pm.positions[fill.symbol]
            cash = getattr(pm, "cash", None)
            print(f"PM qty[{fill.symbol}]={pos.qty} avg={pos.avg_price} cash={cash}", flush=True)
        except Exception as e:
            print(f"PM DIAG ERROR: {e}", flush=True)

        print(f"FILLED paper {fill.symbol} qty={fill.qty} price={fill.price} id={getattr(fill, 'fill_id', None)}",
              flush=True)


def main():
    os.environ.setdefault("EXECUTION_MODE", "paper")

    symbol = os.getenv("SYMBOL") or "GAZP@MISX"
    run_secs = float(os.getenv("RUN_SECS") or "0")
    STARTING_CASH = float(os.getenv("STARTING_CASH", "100000"))

    print(f"Starting PAPER market pipeline. account={ACCOUNT_ID} symbol={symbol}", flush=True)

    bus = EventBus()

    # 1) СОЗДАЁМ pm ОДИН РАЗ
    pm = PositionManager()

    # 2) СТАВИМ СТАРТОВЫЕ ДЕНЬГИ (ровно этому объекту)
    pm.cash = STARTING_CASH
    pm.starting_cash = STARTING_CASH
    pm.starting_capital = STARTING_CASH

    # 3) СОЗДАЁМ portfolio (тоже один раз)
    try:
        portfolio = PortfolioManager(starting_cash=STARTING_CASH)
    except TypeError:
        try:
            portfolio = PortfolioManager(initial_cash=STARTING_CASH)
        except TypeError:
            portfolio = PortfolioManager(STARTING_CASH)

    # 4) ПРОКИДЫВАЕМ pm ВНУТРЬ portfolio (всегда)
    setattr(portfolio, "position_manager", pm)

    risk = RiskEngine()
    paper = PaperExecutionEngine(slippage_coef=0.25, commission=0.0)

    strategy = OnceBuyStrategy(symbol)

    # ВАЖНО: передаём тот же pm в pipeline
    pipeline = PaperTradingPipeline(bus, portfolio, pm, risk, paper, strategy)
    pipeline.attach()

    md = FinamMarketDataClient(bus)
    md.start([symbol])

    t0 = time.time()
    while True:
        time.sleep(1)
        if run_secs > 0 and (time.time() - t0) >= run_secs:
            print("RUN_SECS reached, exit", flush=True)
            return


if __name__ == "__main__":
    main()
