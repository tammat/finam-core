from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


def fetch_one(cur, sql: str):
    cur.execute(sql)
    return dict(cur.fetchone())


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            registry = fetch_one(cur, """
                select
                    count(*) as registry_signals,
                    count(*) filter (where runtime_soft_blocked is true) as soft_blocked,
                    max(ts) as last_registry_ts
                from runtime_guard_signal_registry_v1
            """)

            pre_blocks = fetch_one(cur, """
                select
                    count(*) as pre_signal_blocks,
                    count(*) filter (where block_type = 'VOL_LOW_BLOCK') as vol_low_blocks,
                    count(*) filter (where block_type = 'COMPRESSION_WATCH') as compression_watch_blocks,
                    max(ts) as last_pre_signal_block_ts
                from runtime_guard_pre_signal_block_audit_v1
            """)

            daily = fetch_one(cur, """
                select
                    count(distinct (ts at time zone 'Europe/Moscow')::date) as active_days
                from runtime_guard_pre_signal_block_audit_v1
            """)

            cur.execute("""
                select
                    symbol,
                    strategy,
                    timeframe,
                    block_type,
                    block_reason,
                    ts
                from runtime_guard_pre_signal_block_audit_v1
                order by ts desc
                limit 1
            """)
            last_block = cur.fetchone()

    print("PRE_SIGNAL_BLOCK_RUNTIME_HEALTHCHECK_V1", flush=True)

    print(
        "PRE_SIGNAL_BLOCK_HEALTH_REGISTRY",
        f"registry_signals={registry['registry_signals']}",
        f"soft_blocked={registry['soft_blocked']}",
        f"last_registry_ts={registry['last_registry_ts']}",
        flush=True,
    )

    print(
        "PRE_SIGNAL_BLOCK_HEALTH_BLOCKS",
        f"pre_signal_blocks={pre_blocks['pre_signal_blocks']}",
        f"vol_low_blocks={pre_blocks['vol_low_blocks']}",
        f"compression_watch_blocks={pre_blocks['compression_watch_blocks']}",
        f"active_days={daily['active_days']}",
        f"last_pre_signal_block_ts={pre_blocks['last_pre_signal_block_ts']}",
        flush=True,
    )

    if last_block:
        r = dict(last_block)
        print(
            "PRE_SIGNAL_BLOCK_HEALTH_LAST_BLOCK",
            f"symbol={r['symbol']}",
            f"strategy={r['strategy']}",
            f"timeframe={r['timeframe']}",
            f"block_type={r['block_type']}",
            f"reason={r['block_reason']}",
            f"ts={r['ts']}",
            flush=True,
        )
    else:
        print("PRE_SIGNAL_BLOCK_HEALTH_LAST_BLOCK none", flush=True)

    print("PRE_SIGNAL_BLOCK_RUNTIME_HEALTHCHECK_V1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
