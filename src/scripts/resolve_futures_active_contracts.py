from __future__ import annotations

import argparse

from finam_core.research.futures_contract_universe_repository import (
    FuturesContractUniverseRepository,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--roots", default="BR,NG,USD")
    parser.add_argument("--roll-days", type=int, default=5)
    parser.add_argument("--research-contracts", type=int, default=3)
    args = parser.parse_args()

    repo = FuturesContractUniverseRepository()
    repo.migrate()

    roots = [x.strip() for x in args.roots.split(",") if x.strip()]

    for root in roots:
        active = repo.resolve_active_contract(
            root_symbol=root,
            roll_days=args.roll_days,
        )
        research = repo.resolve_research_contracts(
            root_symbol=root,
            max_contracts=args.research_contracts,
        )

        print(
            "FUTURES_ACTIVE_CONTRACT "
            f"root={root} contract={active or 'NONE'}",
            flush=True,
        )

        print(
            "FUTURES_RESEARCH_CONTRACTS "
            f"root={root} contracts={','.join(research) if research else 'NONE'}",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
