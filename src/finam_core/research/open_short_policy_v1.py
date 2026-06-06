from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OpenShortPolicyDecisionV1:
    symbol: str
    strategy: str
    allowed: bool
    mode: str
    reason: str


class OpenShortPolicyV1:
    """
    Русский комментарий:
    Research-only policy для допуска OPEN_SHORT.
    Runtime-заявки не отправляет.
    """

    def __init__(self, *, mode: str = "shadow") -> None:
        self.mode = mode

    def evaluate(self, *, symbol: str, strategy: str, action: str) -> OpenShortPolicyDecisionV1:
        root = self._root_symbol(symbol)

        if action != "OPEN_SHORT":
            return OpenShortPolicyDecisionV1(
                symbol=symbol,
                strategy=strategy,
                allowed=True,
                mode=self.mode,
                reason="not_open_short",
            )

        if self.mode == "disabled":
            return OpenShortPolicyDecisionV1(
                symbol=symbol,
                strategy=strategy,
                allowed=False,
                mode=self.mode,
                reason="open_short_disabled",
            )

        if root == "BR":
            return OpenShortPolicyDecisionV1(
                symbol=symbol,
                strategy=strategy,
                allowed=True,
                mode=self.mode,
                reason="br_open_short_research_allowed",
            )

        return OpenShortPolicyDecisionV1(
            symbol=symbol,
            strategy=strategy,
            allowed=False,
            mode=self.mode,
            reason="open_short_not_enabled_for_root",
        )

    @staticmethod
    def _root_symbol(symbol: str) -> str:
        s = str(symbol or "").upper()
        if s.startswith("BR"):
            return "BR"
        if s.startswith("NG"):
            return "NG"
        if s.startswith("USDRUB"):
            return "USDRUB"
        if s.startswith("SBER"):
            return "SBER"
        if s.startswith("PLZL"):
            return "PLZL"
        if s.startswith("LKOH"):
            return "LKOH"
        return s.split("@", 1)[0]
