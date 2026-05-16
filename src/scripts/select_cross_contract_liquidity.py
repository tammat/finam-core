from __future__ import annotations

import json

from finam_core.orderflow.cross_contract_liquidity_allocator import CrossContractLiquidityAllocator
from finam_core.storage.postgres_logger import PostgresLogger


INSERT_SQL = """
insert into cross_contract_liquidity_decisions (
    continuous_symbol,
    preferred_symbol,
    score,
    candidates,
    reason,
    raw_json
)
values (%s,%s,%s,%s,%s,%s::jsonb)
"""


def main() -> int:
    pg = PostgresLogger()
    decision = CrossContractLiquidityAllocator(pg).choose_brent()

    if decision is None:
        print("NO_CROSS_CONTRACT_LIQUIDITY_DECISION")
        return 0

    raw = {
        "source": "select_cross_contract_liquidity",
        "continuous_symbol": decision.continuous_symbol,
        "preferred_symbol": decision.preferred_symbol,
        "score": decision.score,
        "candidates": decision.candidates,
        "reason": decision.reason,
    }

    with pg._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                INSERT_SQL,
                (
                    decision.continuous_symbol,
                    decision.preferred_symbol,
                    decision.score,
                    decision.candidates,
                    decision.reason,
                    json.dumps(raw, ensure_ascii=False),
                ),
            )
        conn.commit()

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
