from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioSymbolState:
    symbol: str
    strategy: str
    regime: str
    qty: float
    avg_price: float
    current_price: float
    exposure: float
    unrealized_pnl: float
    realized_pnl: float
    portfolio_weight: float
    strategy_health: str


@dataclass(frozen=True)
class PortfolioIntelligenceSnapshot:
    total_equity: float
    total_exposure: float
    total_unrealized_pnl: float
    total_realized_pnl: float
    total_heat: float
    symbols: list[PortfolioSymbolState]


def build_portfolio_intelligence_snapshot(
    *,
    positions: list[dict],
    strategy_by_symbol: dict[str, str],
    regime_by_symbol: dict[str, str] | None = None,
    realized_pnl_by_symbol: dict[str, float] | None = None,
    strategy_health_by_symbol: dict[str, str] | None = None,
    cash: float = 0.0,
) -> PortfolioIntelligenceSnapshot:
    """
    Русский комментарий:
    Read-only snapshot всего портфеля.

    Ничего не меняет:
    - не отправляет заявки;
    - не меняет RiskEngine;
    - не меняет PortfolioManager;
    - только агрегирует состояние.
    """

    regime_by_symbol = regime_by_symbol or {}
    realized_pnl_by_symbol = realized_pnl_by_symbol or {}
    strategy_health_by_symbol = strategy_health_by_symbol or {}

    raw_states: list[dict] = []

    total_exposure = 0.0
    total_unrealized = 0.0
    total_realized = 0.0

    for pos in positions:
        symbol = str(pos.get("symbol", "")).strip()
        if not symbol:
            continue

        qty = float(pos.get("qty", 0.0) or 0.0)
        avg_price = float(pos.get("avg_price", 0.0) or 0.0)
        current_price = float(pos.get("current_price", avg_price) or 0.0)

        exposure = abs(qty * current_price)
        unrealized_pnl = (current_price - avg_price) * qty
        realized_pnl = float(realized_pnl_by_symbol.get(symbol, 0.0) or 0.0)

        total_exposure += exposure
        total_unrealized += unrealized_pnl
        total_realized += realized_pnl

        raw_states.append(
            {
                "symbol": symbol,
                "strategy": strategy_by_symbol.get(symbol, "UNKNOWN"),
                "regime": regime_by_symbol.get(symbol, "unknown"),
                "qty": qty,
                "avg_price": avg_price,
                "current_price": current_price,
                "exposure": exposure,
                "unrealized_pnl": unrealized_pnl,
                "realized_pnl": realized_pnl,
                "strategy_health": strategy_health_by_symbol.get(symbol, "unknown"),
            }
        )

    total_equity = float(cash) + total_exposure + total_unrealized

    symbols: list[PortfolioSymbolState] = []

    for row in raw_states:
        portfolio_weight = (
            row["exposure"] / total_exposure
            if total_exposure > 0
            else 0.0
        )

        symbols.append(
            PortfolioSymbolState(
                symbol=row["symbol"],
                strategy=row["strategy"],
                regime=row["regime"],
                qty=round(row["qty"], 10),
                avg_price=round(row["avg_price"], 10),
                current_price=round(row["current_price"], 10),
                exposure=round(row["exposure"], 10),
                unrealized_pnl=round(row["unrealized_pnl"], 10),
                realized_pnl=round(row["realized_pnl"], 10),
                portfolio_weight=round(portfolio_weight, 10),
                strategy_health=row["strategy_health"],
            )
        )

    total_heat = total_exposure / total_equity if total_equity > 0 else 0.0

    return PortfolioIntelligenceSnapshot(
        total_equity=round(total_equity, 10),
        total_exposure=round(total_exposure, 10),
        total_unrealized_pnl=round(total_unrealized, 10),
        total_realized_pnl=round(total_realized, 10),
        total_heat=round(total_heat, 10),
        symbols=symbols,
    )
