from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import requests


@dataclass(frozen=True)
class MoexSymbol:
    original_symbol: str
    symbol: str
    engine: str
    market: str
    board: str
    asset_class: str


class MoexSymbolResolver:
    """Русский комментарий: определяет параметры MOEX ISS для внутреннего symbol."""

    def __init__(self, *, timeout_sec: float = 20.0) -> None:
        self.timeout_sec = timeout_sec

    def resolve(self, symbol: str) -> MoexSymbol:
        original = str(symbol).strip()
        base = original.split("@", 1)[0].strip()

        if not base:
            raise ValueError("Пустой symbol")

        # Русский комментарий: быстрый путь для уже принятой внутренней нотации проекта.
        if original.endswith("@MISX"):
            return self._equity(original, base)

        if original.endswith("@RTSX"):
            return self._futures(original, base)

        # Русский комментарий: fallback через MOEX description, если symbol без суффикса площадки.
        return self._resolve_from_moex_description(original, base)

    def _resolve_from_moex_description(self, original: str, base: str) -> MoexSymbol:
        url = f"https://iss.moex.com/iss/securities/{base}.json"

        response = requests.get(url, timeout=self.timeout_sec)
        response.raise_for_status()

        data: dict[str, Any] = response.json()

        description = data.get("description") or {}
        columns = description.get("columns") or []
        rows = description.get("data") or []

        idx = {name: i for i, name in enumerate(columns)}
        values: dict[str, Any] = {}

        for row in rows:
            name = str(row[idx["name"]])
            values[name] = row[idx["value"]]

        group = str(values.get("GROUP") or "")
        sec_type = str(values.get("TYPE") or "")

        if group == "stock_shares" or sec_type in {"common_share", "preferred_share"}:
            return self._equity(original, base)

        if group == "futures_forts" or sec_type == "futures":
            return self._futures(original, base)

        raise ValueError(
            f"Не удалось определить параметры MOEX для symbol={original}: "
            f"group={group} type={sec_type}"
        )

    @staticmethod
    def _equity(original: str, base: str) -> MoexSymbol:
        return MoexSymbol(
            original_symbol=original,
            symbol=base,
            engine="stock",
            market="shares",
            board="TQBR",
            asset_class="equity",
        )

    @staticmethod
    def _futures(original: str, base: str) -> MoexSymbol:
        return MoexSymbol(
            original_symbol=original,
            symbol=base,
            engine="futures",
            market="forts",
            board="RFUD",
            asset_class="futures",
        )
