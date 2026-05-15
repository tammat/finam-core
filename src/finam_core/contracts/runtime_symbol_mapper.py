from __future__ import annotations

from finam_core.contracts.contract_identity_resolver import ContractIdentityResolver


class RuntimeSymbolMapper:
    """
    Русский комментарий:
    Runtime/analytics слой работает через continuous symbol.
    Execution всегда остаётся на raw contract symbol.
    """

    @staticmethod
    def runtime_symbol(symbol: str) -> str:
        identity = ContractIdentityResolver.resolve(symbol)

        if identity.is_futures and identity.continuous:
            return identity.continuous

        return symbol
