from __future__ import annotations

from finam_core.common.strategy_names import normalize_strategy_name

import argparse

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.runtime.strategy_lifecycle_repository import StrategyLifecycleRepository
from finam_core.runtime.strategy_lifecycle_state_machine import (
    StrategyLifecycleInput,
    decide_strategy_lifecycle,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol")
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    database_url = build_psycopg_url()

    where = ""
    params = []

    if args.symbol:
        where = "WHERE p.symbol = %s"
        params.append(args.symbol)

    sql = f"""
    SELECT
        p.symbol,
        p.strategy,
        p.timeframe,
        p.runtime_action,
        COALESCE(r.score, 0),
        COALESCE(r.rank_status, '')
    FROM strategy_promotion_runtime_feed p
    LEFT JOIN strategy_ranking_v2 r
      ON r.symbol = p.symbol
     AND r.strategy = p.strategy
     AND r.timeframe = p.timeframe
     AND r.trade_source = p.trade_source
    {where}
    ORDER BY p.updated_at DESC
    LIMIT %s
    """
    params.append(args.limit)

    decisions = []

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            for row in cur.fetchall():
                decisions.append(
                    decide_strategy_lifecycle(
                        StrategyLifecycleInput(
                            symbol=str(row[0]),
                            strategy=normalize_strategy_name(str(row[1])),
                            timeframe=str(row[2]),
                            runtime_action=str(row[3]),
                            score=float(row[4] or 0.0),
                            rank_status=str(row[5] or ""),
                        )
                    )
                )

    saved = 0
    if args.migrate or args.save:
        repo = StrategyLifecycleRepository(database_url)
        repo.migrate()

    if args.save:
        saved = repo.save(decisions)

    for item in decisions:
        print(
            "STRATEGY_LIFECYCLE_STATE "
            f"symbol={item.symbol} "
            f"strategy={item.strategy} "
            f"timeframe={item.timeframe} "
            f"state={item.lifecycle_state} "
            f"runtime={item.allow_runtime} "
            f"radar={item.allow_radar} "
            f"research={item.allow_research} "
            f"reason={item.reason}",
            flush=True,
        )

    print(
        "STRATEGY_LIFECYCLE_STATE_SUMMARY "
        f"total={len(decisions)} saved={saved}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
