from __future__ import annotations

import argparse

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.runtime.strategy_promotion_feed_repository import StrategyPromotionFeedRepository
from finam_core.runtime.strategy_promotion_feed import (
    StrategyPromotionInput,
    build_strategy_promotion_decision,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    where = ""
    params = []

    if args.symbol:
        where = "WHERE symbol = %s"
        params.append(args.symbol)

    sql = f"""
    SELECT symbol, strategy, timeframe, trade_source,
           score, rank_status, reason
    FROM strategy_ranking_v2
    {where}
    ORDER BY score DESC, calculated_at DESC
    LIMIT %s
    """
    params.append(args.limit)

    decisions = []

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            for row in cur.fetchall():
                decisions.append(
                    build_strategy_promotion_decision(
                        StrategyPromotionInput(
                            symbol=str(row[0]),
                            strategy=str(row[1]),
                            timeframe=str(row[2]),
                            trade_source=str(row[3]),
                            score=float(row[4] or 0.0),
                            rank_status=str(row[5]),
                            reason=str(row[6]),
                        )
                    )
                )

    saved = 0
    if args.migrate or args.save:
        feed_repo = StrategyPromotionFeedRepository(build_psycopg_url())
        feed_repo.migrate()

    if args.save:
        saved = feed_repo.save(decisions)

    for item in decisions:
        print(
            "STRATEGY_PROMOTION_FEED "
            f"symbol={item.symbol} "
            f"strategy={item.strategy} "
            f"timeframe={item.timeframe} "
            f"source={item.trade_source} "
            f"action={item.runtime_action} "
            f"paper={item.allow_paper_signal} "
            f"radar={item.allow_radar_signal} "
            f"real_suggestion={item.allow_real_suggestion} "
            f"reason={item.reason}",
            flush=True,
        )

    print(
        "STRATEGY_PROMOTION_FEED_SUMMARY "
        f"total={len(decisions)} saved={saved}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
