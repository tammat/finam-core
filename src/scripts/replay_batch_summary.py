from __future__ import annotations

import argparse

from finam_core.storage.postgres_logger import PostgresLogger


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--batch-id", required=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    pg = PostgresLogger()

    sql = """
    with campaigns as (
        select distinct campaign_id
        from replay_campaign_runs
        where campaign_id like %s
    ),
    run_stats as (
        select
            count(*) as runs,
            count(*) filter (where status = 'success') as success,
            count(*) filter (where status <> 'success') as failed,
            round(avg(duration_sec)::numeric, 2) as avg_duration_sec,
            count(distinct symbol) as symbols,
            count(distinct strategy) as strategies
        from replay_campaign_runs
        where campaign_id like %s
    ),
    closed_stats as (
        select
            count(*) as closed_trades,
            round(coalesce(sum(net_pnl), 0)::numeric, 6) as net_pnl,
            round(coalesce(avg(case when net_pnl > 0 then 1 else 0 end), 0)::numeric, 4) as winrate,
            round(coalesce(avg(net_pnl), 0)::numeric, 6) as expectancy
        from closed_trades
        where coalesce(
            payload->>'replay_campaign_id',
            payload->'payload'->>'replay_campaign_id'
        ) like %s
          and trade_source = 'paper'
    )
    select
        (select count(*) from campaigns) as campaigns,
        rs.runs,
        rs.success,
        rs.failed,
        rs.avg_duration_sec,
        rs.symbols,
        rs.strategies,
        cs.closed_trades,
        cs.net_pnl,
        cs.winrate,
        cs.expectancy
    from run_stats rs
    cross join closed_stats cs
    """

    pattern = f"{args.batch_id}-%"

    with pg._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (pattern, pattern, pattern))
            row = cur.fetchone()

    print(
        "REPLAY_BATCH_SUMMARY "
        f"batch_id={args.batch_id} "
        f"campaigns={row[0]} "
        f"runs={row[1]} "
        f"success={row[2]} "
        f"failed={row[3]} "
        f"avg_duration_sec={row[4]} "
        f"symbols={row[5]} "
        f"strategies={row[6]} "
        f"closed_trades={row[7]} "
        f"net_pnl={row[8]} "
        f"winrate={row[9]} "
        f"expectancy={row[10]}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
