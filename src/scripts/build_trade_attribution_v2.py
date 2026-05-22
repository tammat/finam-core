from __future__ import annotations

import argparse

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.analytics.trade_attribution_v2_repository import (
    TradeAttributionV2Repository,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    repo = TradeAttributionV2Repository(build_psycopg_url())

    if args.migrate or args.save:
        repo.migrate()

    items = repo.build(symbol=args.symbol, limit=args.limit)

    saved = 0
    if args.save:
        saved = repo.save(items)

    full = sum(1 for x in items if x.attribution_quality == "FULL")
    partial = sum(1 for x in items if x.attribution_quality == "PARTIAL")
    weak = sum(1 for x in items if x.attribution_quality == "RISK_CONTEXT_WEAK")

    for item in items[:20]:
        print(
            "TRADE_ATTRIBUTION_V2 "
            f"closed_trade_id={item.closed_trade_id} "
            f"symbol={item.symbol} "
            f"strategy={item.strategy} "
            f"timeframe={item.timeframe} "
            f"pnl={round(item.pnl, 6)} "
            f"heat_status={item.heat_status} "
            f"risk_multiplier={item.risk_multiplier} "
            f"lifecycle_action={item.lifecycle_action} "
            f"exit_policy={item.exit_policy} "
            f"quality={item.attribution_quality} "
            f"reason={item.reason}",
            flush=True,
        )

    print(
        "TRADE_ATTRIBUTION_V2_SUMMARY "
        f"symbol={args.symbol} "
        f"total={len(items)} "
        f"full={full} "
        f"partial={partial} "
        f"risk_context_weak={weak} "
        f"saved={saved}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
