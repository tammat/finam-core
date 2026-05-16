from __future__ import annotations

from finam_core.orderflow.cross_contract_liquidity_allocator import CrossContractLiquidityAllocator
from finam_core.storage.postgres_logger import PostgresLogger


def main() -> int:
    decision = CrossContractLiquidityAllocator(PostgresLogger()).choose_brent()

    if decision is None:
        print("NO_CROSS_CONTRACT_LIQUIDITY_DECISION")
        return 0

    print(
        "OK: cross contract liquidity "
        f"continuous={decision.continuous_symbol} "
        f"preferred={decision.preferred_symbol} "
        f"score={decision.score} "
        f"reason={decision.reason}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
