from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TradePathInput:
    trade_index: int
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    qty: float
    pnl: float


@dataclass(frozen=True)
class ReconstructedTradePath:
    trade_index: int
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    qty: float
    pnl: float
    reconstructed_high: float
    reconstructed_low: float
    reconstructed_mae: float
    reconstructed_mfe: float
    exit_efficiency: float
    path_confidence: float
    reconstruction_mode: str


def reconstruct_trade_path(
    trade: TradePathInput,
    adverse_ratio: float = 0.35,
    favorable_ratio: float = 0.65,
) -> ReconstructedTradePath:
    """
    Русский комментарий:
    Консервативно восстанавливает путь сделки, если нет сохранённых OHLC-баров.

    Назначение:
    - не заменяет реальные market_bars;
    - даёт fallback для MAE/MFE и exit optimization;
    - используется только для аналитики качества выходов.

    Для long:
    - прибыльная сделка: допускаем, что цена сначала дала часть adverse move,
      затем прошла выше exit;
    - убыточная сделка: допускаем небольшой favorable move перед уходом в убыток.
    """

    side = trade.side.lower().strip()
    entry = float(trade.entry_price)
    exit_ = float(trade.exit_price)
    qty = float(trade.qty)
    pnl = float(trade.pnl)

    move = abs(exit_ - entry)
    base_range = max(move, abs(pnl) / max(qty, 1.0), entry * 0.001)

    if side in {"long", "buy"}:
        if exit_ >= entry:
            reconstructed_low = entry - base_range * adverse_ratio
            reconstructed_high = exit_ + base_range * favorable_ratio
        else:
            reconstructed_low = exit_ - base_range * adverse_ratio
            reconstructed_high = entry + base_range * favorable_ratio

        mfe = reconstructed_high - entry
        mae = reconstructed_low - entry
        raw_exit_move = exit_ - entry

    elif side in {"short", "sell"}:
        if exit_ <= entry:
            reconstructed_high = entry + base_range * adverse_ratio
            reconstructed_low = exit_ - base_range * favorable_ratio
        else:
            reconstructed_high = exit_ + base_range * adverse_ratio
            reconstructed_low = entry - base_range * favorable_ratio

        mfe = entry - reconstructed_low
        mae = entry - reconstructed_high
        raw_exit_move = entry - exit_

    else:
        reconstructed_high = max(entry, exit_)
        reconstructed_low = min(entry, exit_)
        mfe = max(exit_ - entry, 0.0)
        mae = min(exit_ - entry, 0.0)
        raw_exit_move = exit_ - entry

    exit_efficiency = raw_exit_move / mfe if mfe > 0 else 0.0

    return ReconstructedTradePath(
        trade_index=trade.trade_index,
        symbol=trade.symbol,
        side=side,
        entry_price=round(entry, 10),
        exit_price=round(exit_, 10),
        qty=round(qty, 10),
        pnl=round(pnl, 10),
        reconstructed_high=round(reconstructed_high, 10),
        reconstructed_low=round(reconstructed_low, 10),
        reconstructed_mae=round(mae, 10),
        reconstructed_mfe=round(mfe, 10),
        exit_efficiency=round(exit_efficiency, 10),
        path_confidence=0.35,
        reconstruction_mode="fallback_trade_path",
    )


def reconstruct_trade_paths(
    trades: list[TradePathInput],
) -> list[ReconstructedTradePath]:
    return [reconstruct_trade_path(trade) for trade in trades]
