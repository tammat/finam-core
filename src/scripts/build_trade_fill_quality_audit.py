from __future__ import annotations

import argparse

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.analytics.trade_fill_quality_audit_repository import (
    TradeFillQualityAuditRepository,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--trade-source", default="paper")
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    repo = TradeFillQualityAuditRepository(build_psycopg_url())

    if args.migrate or args.save:
        repo.migrate()

    decision = repo.build(
        symbol=args.symbol,
        trade_source=args.trade_source,
    )

    if args.save:
        repo.save(decision)

    print(
        "TRADE_FILL_QUALITY_AUDIT "
        f"symbol={decision.symbol} "
        f"source={decision.trade_source} "
        f"total={decision.total_fills} "
        f"buy={decision.buy_fills} "
        f"sell={decision.sell_fills} "
        f"missing_strategy={decision.missing_strategy} "
        f"missing_timeframe={decision.missing_timeframe} "
        f"backfill={decision.backfill_fills} "
        f"status={decision.status} "
        f"allowed={decision.reconstruction_allowed} "
        f"reason={decision.reason}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
