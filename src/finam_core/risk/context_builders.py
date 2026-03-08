# src/finam_core/risk/context_builders.py
# Русский коммент: сборка RiskContext (SimpleNamespace) для RiskStack без жесткой привязки к PortfolioManager.

from __future__ import annotations

from types import SimpleNamespace


def _safe_float(x, default=0.0) -> float:
    try:
        if x is None:
            return float(default)
        return float(x)
    except Exception:
        return float(default)


def _get_price_from_state(st: dict, side: str) -> float:
    # Русский коммент: берём last, иначе BUY->ask / SELL->bid
    last = st.get("last")
    bid = st.get("bid")
    ask = st.get("ask")
    px = last if last is not None else (ask if side.upper() == "BUY" else bid)
    return _safe_float(px, default=0.0)


def _get_position_qty_from_pm(pm, symbol: str) -> float:
    try:
        pos = pm.positions.get(symbol)
        if pos is None:
            return 0.0
        return _safe_float(getattr(pos, "qty", 0.0), default=0.0)
    except Exception:
        return 0.0


def build_risk_context(intent: dict, portfolio, market_state: dict) -> SimpleNamespace:
    """
    Русский коммент: минимальный контекст под правила RiskStack.
    Добавляй поля только по мере потребности новых правил.
    """
    sym = intent.get("symbol")
    side = str(intent.get("side", "BUY")).upper()
    qty = _safe_float(intent.get("qty", intent.get("quantity", 0)) or 0.0, default=0.0)

    px = _get_price_from_state(market_state, side)
    trade_value = abs(qty) * px

    # best-effort portfolio metrics
    total_exposure = getattr(portfolio, "total_exposure", None)
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

    daily_realized_pnl = getattr(portfolio, "daily_realized_pnl", None)
    if daily_realized_pnl is None:
        daily_realized_pnl = getattr(getattr(portfolio, "position_manager", None), "daily_realized_pnl", 0.0)

    portfolio_heat = getattr(portfolio, "portfolio_heat", None)
    if portfolio_heat is None:
        portfolio_heat = 0.0

    # current_symbol_exposure
    pm = getattr(portfolio, "position_manager", None)
    pos_qty = _get_position_qty_from_pm(pm, sym) if pm is not None else 0.0
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