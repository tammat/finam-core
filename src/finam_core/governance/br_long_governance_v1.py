from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BrLongMode(str, Enum):
    ENABLED = "enabled"
    SHADOW = "shadow"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class BrLongGovernanceDecision:
    symbol: str
    side: str
    mode: str
    allowed: bool
    shadow_logged: bool
    reason: str


class BrLongGovernanceV1:
    """
    Governance-фильтр BR LONG.

    Назначение:
    - не удаляет стратегию;
    - не меняет Exit Engine;
    - позволяет формально перевести BR LONG в shadow/disabled;
    - используется как отдельный слой принятия решения.

    Runtime здесь не подключается.
    """

    def __init__(self, mode: str = "shadow"):
        normalized = str(mode or "shadow").lower()

        if normalized not in {m.value for m in BrLongMode}:
            normalized = BrLongMode.SHADOW.value

        self.mode = BrLongMode(normalized)

    def evaluate(self, *, symbol: str, side: str) -> BrLongGovernanceDecision:
        normalized_symbol = str(symbol or "")
        normalized_side = str(side or "").upper()

        is_br = normalized_symbol.startswith("BR")
        is_long = normalized_side in {"BUY", "LONG"}

        if not is_br or not is_long:
            return BrLongGovernanceDecision(
                symbol=normalized_symbol,
                side=normalized_side,
                mode=self.mode.value,
                allowed=True,
                shadow_logged=False,
                reason="not_br_long",
            )

        if self.mode == BrLongMode.ENABLED:
            return BrLongGovernanceDecision(
                symbol=normalized_symbol,
                side=normalized_side,
                mode=self.mode.value,
                allowed=True,
                shadow_logged=False,
                reason="br_long_enabled",
            )

        if self.mode == BrLongMode.DISABLED:
            return BrLongGovernanceDecision(
                symbol=normalized_symbol,
                side=normalized_side,
                mode=self.mode.value,
                allowed=False,
                shadow_logged=False,
                reason="br_long_disabled_after_negative_clean_edge",
            )

        return BrLongGovernanceDecision(
            symbol=normalized_symbol,
            side=normalized_side,
            mode=self.mode.value,
            allowed=False,
            shadow_logged=True,
            reason="br_long_shadow_after_negative_clean_edge",
        )
