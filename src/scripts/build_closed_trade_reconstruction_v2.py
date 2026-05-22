from __future__ import annotations

import argparse

from finam_core.analytics.closed_trade_reconstruction_v2_repository import (
    ClosedTradeReconstructionV2Repository,
)
from finam_core.analytics.statistics_repository import build_psycopg_url


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--trade-source", default="paper")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--migrate", action="store_true")
    args = parser.parse_args()

    repo = ClosedTradeReconstructionV2Repository(build_psycopg_url())

    if args.migrate:
        repo.migrate()

    reconstructed, inserted = repo.rebuild_symbol(
        symbol=args.symbol,
        trade_source=args.trade_source,
        limit=args.limit,
    )

    print(
        "CLOSED_TRADE_RECONSTRUCTION_V2_OK "
        f"symbol={args.symbol} "
        f"trade_source={args.trade_source} "
        f"reconstructed={reconstructed} "
        f"inserted={inserted}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
