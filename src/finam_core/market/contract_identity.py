from __future__ import annotations

from dataclasses import dataclass

from finam_core.contracts.contract_identity_resolver import (
    ContractIdentityResolver as CanonicalContractIdentityResolver,
)


@dataclass(frozen=True)
class ContractIdentity:
    symbol: str
    root_symbol: str
    continuous_symbol: str
    contract_code: str | None


class ContractIdentityResolver:
    """Русский комментарий: compatibility wrapper над canonical contracts resolver."""

    def resolve(self, symbol: str) -> ContractIdentity:
        identity = CanonicalContractIdentityResolver.resolve(symbol)

        contract_code = None
        if identity.is_futures:
            contract_code = f"{identity.month_code}{identity.year_code}"

        return ContractIdentity(
            symbol=identity.symbol,
            root_symbol=identity.root,
            continuous_symbol=identity.continuous if identity.is_futures else identity.symbol,
            contract_code=contract_code,
        )
