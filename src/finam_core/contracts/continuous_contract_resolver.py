from __future__ import annotations

from finam_core.contracts.contract_identity_resolver import ContractIdentityResolver


_CONTINUOUS_BY_ROOT = {
    "BR": "BR_CONT",
    "NG": "NG_CONT",
    "SI": "SI_CONT",
    "USD": "SI_CONT",
}


class ContinuousContractResolver:
    """Русский комментарий: определяет research/analytics continuous symbol без изменения execution symbol."""

    @staticmethod
    def resolve(symbol: str) -> str:
        identity = ContractIdentityResolver.resolve(symbol)

        continuous = getattr(identity, "continuous", None) or getattr(identity, "continuous_symbol", None)
        if continuous:
            return str(continuous)

        root = getattr(identity, "root", None) or getattr(identity, "root_symbol", None)

        if root:
            return _CONTINUOUS_BY_ROOT.get(str(root), str(symbol))

        return str(symbol)
