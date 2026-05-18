from __future__ import annotations

import argparse

from finam_core.storage.postgres_logger import PostgresLogger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-id", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pg = PostgresLogger()

    sql = """
    with campaign_window as (
        select
            min(started_at) as started_at,
            max(finished_at) as finished_at
        from replay_campaign_runs
        where campaign_id = %s
    )
    select
        ct.symbol,
        coalesce(ct.strategy, 'unknown') as strategy,
        coalesce(ct.horizon, 'unknown') as timeframe,
        count(*) as closed_trades,
        round(sum(ct.net_pnl)::numeric, 4) as net_pnl,
        round(avg(case when ct.net_pnl > 0 then 1 else 0 end)::numeric, 4) as winrate,
        round(avg(ct.net_pnl)::numeric, 4) as expectancy
    from closed_trades ct
    cross join campaign_window cw
    where cw.started_at is not null
      and ct.created_at >= cw.started_at
      and ct.created_at <= coalesce(cw.finished_at, now())
      and ct.trade_source = 'paper'
    group by ct.symbol, coalesce(ct.strategy, 'unknown'), coalesce(ct.horizon, 'unknown')
    order by net_pnl desc
    """

    with pg._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (args.campaign_id,))
            rows = cur.fetchall()

    if not rows:
        print(f"REPLAY_CAMPAIGN_PERFORMANCE_EMPTY campaign_id={args.campaign_id}", flush=True)
        return 0

    for row in rows:
        print(
            "REPLAY_CAMPAIGN_PERFORMANCE "
            f"campaign_id={args.campaign_id} "
            f"symbol={row[0]} "
            f"strategy={row[1]} "
            f"timeframe={row[2]} "
            f"closed_trades={row[3]} "
            f"net_pnl={row[4]} "
            f"winrate={row[5]} "
            f"expectancy={row[6]}",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
