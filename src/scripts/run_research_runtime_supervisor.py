from __future__ import annotations

import argparse

from finam_core.research.research_runtime_supervisor import (
    ResearchRuntimeSupervisor,
    ResearchRuntimeSupervisorConfig,
)


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

    symbols = [x.strip() for x in args.symbols.split(",") if x.strip()]

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
