# src/finam_core/accounting/portfolio_bootstrap.py

from __future__ import annotations

import json
from pathlib import Path


def load_portfolio_snapshot(path: str) -> dict:
    """
    Русский коммент: единый формат стартового снимка портфеля.
    Позже сюда будет писать Finam portfolio provider.
    """
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))

    cash = float(data.get("cash", 0.0))
    starting_cash = float(data.get("starting_cash", cash))
    positions = data.get("positions", {}) or {}

    return {
        "cash": cash,
        "starting_cash": starting_cash,
        "realized_pnl": float(data.get("realized_pnl", 0.0)),
        "daily_realized_pnl": float(data.get("daily_realized_pnl", 0.0)),
        "peak_equity": float(data.get("peak_equity", starting_cash)),
        "positions": positions,
    }


def bootstrap_position_manager(position_manager, snapshot: dict) -> None:
    """
    Русский коммент: инициализация PositionManager из внешнего снимка.
    Работает без зависимости от restore_snapshot().
    """
    cash = float(snapshot.get("cash", 0.0))
    starting_cash = float(snapshot.get("starting_cash", cash))
    positions = snapshot.get("positions", {}) or {}

    position_manager.cash = cash
    position_manager.starting_cash = starting_cash
    position_manager.starting_capital = starting_cash

    if hasattr(position_manager, "realized_pnl"):
        position_manager.realized_pnl = float(snapshot.get("realized_pnl", 0.0))

    if hasattr(position_manager, "daily_realized_pnl"):
        position_manager.daily_realized_pnl = float(snapshot.get("daily_realized_pnl", 0.0))

    if hasattr(position_manager, "_peak_equity"):
        position_manager._peak_equity = float(snapshot.get("peak_equity", starting_cash))

    if hasattr(position_manager, "positions"):
        position_manager.positions.clear()

        for symbol, data in positions.items():
            pos = position_manager.positions[symbol]
            pos.symbol = symbol
            pos.qty = float(data.get("qty", 0.0))
            pos.avg_price = float(data.get("avg_price", data.get("price", 0.0)))
            pos.mark_price = float(data.get("mark_price", pos.avg_price))

            if hasattr(pos, "realized_pnl"):
                pos.realized_pnl = float(data.get("realized_pnl", 0.0))
