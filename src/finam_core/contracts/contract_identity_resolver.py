from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ContractIdentity:
    """Русский комментарий: единая идентичность инструмента для futures/spot analytics."""
    symbol: str
    root: str
    continuous: str
    venue: str
    month_code: str | None = None
    year_code: str | None = None
    is_futures: bool = False


class ContractIdentityResolver:
    """
    Русский комментарий:
    Преобразует конкретный контракт фьючерса в continuous identity.

    Примеры:
    BRM6@RTSX    -> root=BR,     continuous=BR_CONT
    BRN6@RTSX    -> root=BR,     continuous=BR_CONT
    NGH6@RTSX    -> root=NG,     continuous=NG_CONT
    USDRUBF@RTSX -> root=USDRUB, continuous=USDRUB_CONT

    Execution всегда остаётся на symbol.
    Analytics/runtime/regime могут использовать continuous.
    """

    FUTURES_PATTERN = re.compile(
        r"^([A-Z]+)([FGHJKMNQUVXZ])(\d*)@([A-Z]+)$"
    )

    @classmethod
    def resolve(cls, symbol: str) -> ContractIdentity:
        normalized_symbol = str(symbol or "").strip()

        if "@" in normalized_symbol:
            left, venue = normalized_symbol.split("@", 1)
        else:
            left, venue = normalized_symbol, "UNKNOWN"

        match = cls.FUTURES_PATTERN.match(normalized_symbol)

        # Русский комментарий: futures-логика применяется только к срочному рынку RTSX.
        # Иначе акции вроде OZON@MISX ошибочно превращаются в OZO_CONT.
        if venue != "RTSX":
            match = None

        if not match:
            return ContractIdentity(
                symbol=normalized_symbol,
                root=left,
                continuous=left,
                venue=venue,
                is_futures=False,
            )

        root, month_code, year_code, venue = match.groups()

        return ContractIdentity(
            symbol=normalized_symbol,
            root=root,
            continuous=f"{root}_CONT",
            venue=venue,
            month_code=month_code,
            year_code=year_code,
            is_futures=True,
        )
