from __future__ import annotations

import argparse

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.analytics.trade_context_snapshot_repository import (
    TradeContextSnapshotRepository,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    repo = TradeContextSnapshotRepository(build_psycopg_url())

    if args.migrate or args.save:
        repo.migrate()

    items = repo.build(symbol=args.symbol, limit=args.limit)

    saved = 0
    if args.save:
        saved = repo.save(items)

    full = sum(1 for x in items if x.context_quality == "FULL")
    partial = sum(1 for x in items if x.context_quality == "PARTIAL")

    for item in items[:3]:
        print(
            "TRADE_CONTEXT_SNAPSHOT_PREVIEW "
            f"closed_trade_id={item.closed_trade_id} "
            f"symbol={item.symbol} "
            f"strategy={item.strategy} "
            f"timeframe={item.timeframe} "
            f"quality={item.context_quality} "
            f"missing={item.missing_fields}",
            flush=True,
        )

    hidden = max(len(items) - 3, 0)

    if hidden:
        print(
            f"TRADE_CONTEXT_SNAPSHOT_PREVIEW_HIDDEN count={hidden}",
            flush=True,
        )

    print(
        "TRADE_CONTEXT_SNAPSHOT_SUMMARY "
        f"symbol={args.symbol} "
        f"total={len(items)} "
        f"full={full} "
        f"partial={partial} "
        f"saved={saved}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
