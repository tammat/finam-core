from __future__ import annotations

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


TABLES = [
    "strategy_statistics_v2",
    "strategy_ranking_v2",
    "strategy_promotion_runtime_feed",
    "runtime_strategy_selection",
    "strategy_lifecycle_state",
    "strategy_promotion_decisions",
]


def main() -> int:
    deleted_total = 0

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            for table in TABLES:
                cur.execute(
                    f"""
                    DELETE FROM {table}
                    WHERE COALESCE(strategy, '') = ''
                       OR COALESCE(timeframe, '') = ''
                    """
                )
                deleted = cur.rowcount
                deleted_total += deleted
                print(
                    "CLEANUP_INVALID_STRATEGY_ROWS "
                    f"table={table} deleted={deleted}",
                    flush=True,
                )
        conn.commit()

    print(
        "CLEANUP_INVALID_STRATEGY_ROWS_OK "
        f"deleted_total={deleted_total}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
