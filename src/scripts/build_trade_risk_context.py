from __future__ import annotations

import argparse

from finam_core.analytics.trade_risk_context_repository import (
    TradeRiskContextRepository,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    repo = TradeRiskContextRepository()

    if args.migrate or args.save:
        repo.migrate()

    total = full = partial = 0

    if args.save:
        total, full, partial = repo.build_and_save(
            symbol=args.symbol,
            limit=args.limit,
        )

    print(
        "TRADE_RISK_CONTEXT_SUMMARY "
        f"symbol={args.symbol} "
        f"total={total} "
        f"full={full} "
        f"partial={partial}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
