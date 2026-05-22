from __future__ import annotations

import argparse

from finam_core.research.futures_contract_universe_repository import FuturesContractUniverseRepository
from finam_core.research.research_runtime_supervisor import (
    ResearchRuntimeSupervisor,
    ResearchRuntimeSupervisorConfig,
)


def expand_symbol_tokens(symbols: list[str]) -> list[str]:
    """
    Русский комментарий:
    Разворачивает псевдосимволы фьючерсов в реальные контракты.
    *_ACTIVE возвращает один рабочий контракт.
    *_RESEARCH возвращает несколько ближайших контрактов.
    """
    repo = FuturesContractUniverseRepository()
    result: list[str] = []

    for symbol in symbols:
        token = symbol.strip().upper()

        if token.endswith("_ACTIVE"):
            root = token.replace("_ACTIVE", "")
            contract = repo.resolve_active_contract(root_symbol=root)
            if contract:
                result.append(contract)
            continue

        if token.endswith("_RESEARCH"):
            root = token.replace("_RESEARCH", "")
            contracts = repo.resolve_research_contracts(root_symbol=root, max_contracts=3)
            result.extend(contracts)
            continue

        result.append(symbol)

    # Русский комментарий: сохраняем порядок и убираем дубли.
    deduped: list[str] = []
    seen: set[str] = set()

    for symbol in result:
        if symbol not in seen:
            deduped.append(symbol)
            seen.add(symbol)

    return deduped


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="research-supervisor-v1")
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--trade-source", default="paper")
    parser.add_argument("--interval-sec", type=int, default=300)
    parser.add_argument("--limit", type=int, default=20000)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--no-sync-universe", action="store_true")
    args = parser.parse_args()

    symbols = expand_symbol_tokens([x.strip() for x in args.symbols.split(",") if x.strip()])

    supervisor = ResearchRuntimeSupervisor(
        ResearchRuntimeSupervisorConfig(
            supervisor_name=args.name,
            symbols=symbols,
            trade_source=args.trade_source,
            interval_sec=args.interval_sec,
            limit=args.limit,
            once=args.once,
            sync_universe=not args.no_sync_universe,
        )
    )

    return supervisor.run()


if __name__ == "__main__":
    raise SystemExit(main())
