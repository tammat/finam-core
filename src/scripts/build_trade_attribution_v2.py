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

    items = repo.build(
        symbol=args.symbol,
        limit=args.limit,
    )

    saved = 0
    if args.save:
        saved = repo.save(items)

    def item_quality(item) -> str:
        return str(
            getattr(item, "quality", None)
            or getattr(item, "attribution_quality", None)
            or getattr(item, "quality_status", None)
            or ""
        )

    full = sum(1 for item in items if item_quality(item) == "FULL")
    partial = sum(1 for item in items if item_quality(item) == "PARTIAL")
    risk_context_weak = sum(
        1 for item in items if item_quality(item) == "RISK_CONTEXT_WEAK"
    )

    preview_limit = 3

    for item in items[:preview_limit]:
        print(
            "TRADE_ATTRIBUTION_V2_PREVIEW "
            f"closed_trade_id={item.closed_trade_id} "
            f"symbol={item.symbol} "
            f"strategy={item.strategy} "
            f"timeframe={item.timeframe} "
            f"pnl={item.pnl} "
            f"quality={item_quality(item)} "
            f"reason={item.reason}",
            flush=True,
        )

    hidden = max(len(items) - preview_limit, 0)

    if hidden:
        print(
            f"TRADE_ATTRIBUTION_V2_PREVIEW_HIDDEN count={hidden}",
            flush=True,
        )

    print(
        "TRADE_ATTRIBUTION_V2_SUMMARY "
        f"symbol={args.symbol} "
        f"total={len(items)} "
        f"full={full} "
        f"partial={partial} "
        f"risk_context_weak={risk_context_weak} "
        f"saved={saved}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
