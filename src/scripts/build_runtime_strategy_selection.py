from __future__ import annotations

import argparse

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.runtime.runtime_strategy_selector import (
    RuntimeStrategyCandidate,
    select_runtime_strategy,
)

from finam_core.runtime.runtime_strategy_selection_repository import (
    RuntimeStrategySelectionRepository,
    RuntimeStrategySelectionRecord,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    repo = RuntimeStrategySelectionRepository()
    repo.migrate()

    where = ""
    params = []

    if args.symbol:
        where = "WHERE symbol = %s"
        params.append(args.symbol)

    sql = f"""
    SELECT
        symbol,
        strategy,
        timeframe,
        trade_source,
        runtime_action,
        allow_paper_signal,
        allow_radar_signal,
        allow_real_suggestion
    FROM strategy_promotion_runtime_feed
    {where}
    ORDER BY updated_at DESC
    LIMIT %s
    """
    params.append(args.limit)

    selections = []

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            for row in cur.fetchall():
                selections.append(
                    select_runtime_strategy(
                        RuntimeStrategyCandidate(
                            symbol=str(row[0]),
                            strategy=str(row[1]),
                            timeframe=str(row[2]),
                            trade_source=str(row[3]),
                            runtime_action=str(row[4]),
                            allow_paper_signal=bool(row[5]),
                            allow_radar_signal=bool(row[6]),
                            allow_real_suggestion=bool(row[7]),
                        )
                    )
                )

    for item in selections:
        repo.save(
            RuntimeStrategySelectionRecord(
                symbol=item.symbol,
                strategy=item.strategy,
                timeframe=item.timeframe,
                mode=item.mode,
                enabled=item.enabled,
                reason=item.reason,
                updated_at=repo.now_utc(),
            )
        )

        print(
            "RUNTIME_STRATEGY_SELECTION "
            f"symbol={item.symbol} "
            f"strategy={item.strategy} "
            f"timeframe={item.timeframe} "
            f"mode={item.mode} "
            f"enabled={item.enabled} "
            f"reason={item.reason}",
            flush=True,
        )

    print(
        "RUNTIME_STRATEGY_SELECTION_SUMMARY "
        f"total={len(selections)} "
        f"enabled={sum(1 for x in selections if x.enabled)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
