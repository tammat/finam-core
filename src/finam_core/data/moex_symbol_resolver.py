from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MoexSymbol:
    original_symbol: str
    symbol: str
    engine: str
    market: str
    board: str
    asset_class: str


class MoexSymbolResolver:
    """Русский комментарий: преобразует внутренний symbol проекта в параметры MOEX ISS."""

    EQUITY_BOARD = "TQBR"

    FUTURES_BOARD = "RFUD"

    def resolve(self, symbol: str) -> MoexSymbol:
        original = str(symbol).strip()
        base = original.split("@", 1)[0].strip()

        if not base:
            raise ValueError("Пустой symbol")

        if original.endswith("@MISX"):
            return MoexSymbol(
                original_symbol=original,
                symbol=base,
                engine="stock",
                market="shares",
                board=self.EQUITY_BOARD,
                asset_class="equity",
            )

        if original.endswith("@RTSX"):
            return MoexSymbol(
                original_symbol=original,
                symbol=base,
                engine="futures",
                market="forts",
                board=self.FUTURES_BOARD,
                asset_class="futures",
            )

        if base in {"SBER", "LKOH", "PLZL", "GAZP", "NVTK", "SBERP", "VTBR", "OZON"}:
            return MoexSymbol(
                original_symbol=original,
                symbol=base,
                engine="stock",
                market="shares",
                board=self.EQUITY_BOARD,
                asset_class="equity",
            )

        if base.startswith(("BR", "NG", "Si", "SI")) or base == "USDRUBF":
            return MoexSymbol(
                original_symbol=original,
                symbol=base,
                engine="futures",
                market="forts",
                board=self.FUTURES_BOARD,
                asset_class="futures",
            )

        raise ValueError(f"Не удалось определить параметры MOEX для symbol={symbol}")
