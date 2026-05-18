from __future__ import annotations

import argparse

from finam_core.storage.postgres_logger import PostgresLogger


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--sweep-id", required=True)
    p.add_argument("--limit", type=int, default=20)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    pg = PostgresLogger()

    sql = """
    select
        coalesce(
            payload->>'replay_campaign_id',
            payload->'payload'->>'replay_campaign_id'
        ) as campaign_id,
        count(*) as trades,
        round(sum(net_pnl)::numeric, 6) as net_pnl,
        round(avg(net_pnl)::numeric, 6) as expectancy,
        round(avg(case when net_pnl > 0 then 1 else 0 end)::numeric, 4) as winrate
    from closed_trades
    where coalesce(
        payload->>'replay_campaign_id',
        payload->'payload'->>'replay_campaign_id'
    ) like %s
      and trade_source = 'paper'
    group by campaign_id
    order by expectancy desc, net_pnl desc
    limit %s
    """

    with pg._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (f"{args.sweep_id}-%", args.limit))
            rows = cur.fetchall()

    if not rows:
        print(f"PARAM_SWEEP_SUMMARY_EMPTY sweep_id={args.sweep_id}", flush=True)
        return 0

    for row in rows:
        print(
            "PARAM_SWEEP_SUMMARY "
            f"sweep_id={args.sweep_id} "
            f"campaign_id={row[0]} "
            f"trades={row[1]} "
            f"net_pnl={row[2]} "
            f"expectancy={row[3]} "
            f"winrate={row[4]}",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
