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
    select
        campaign_id,
        count(*) as runs,
        count(*) filter (where status = 'success') as success,
        count(*) filter (where status <> 'success') as failed,
        round(avg(duration_sec)::numeric, 2) as avg_duration_sec,
        count(distinct symbol) as symbols,
        count(distinct strategy) as strategies
    from replay_campaign_runs
    where campaign_id = %s
    group by campaign_id
    """

    with pg._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (args.campaign_id,))
            row = cur.fetchone()

    if row is None:
        print(f"REPLAY_CAMPAIGN_SUMMARY_EMPTY campaign_id={args.campaign_id}", flush=True)
        return 1

    print(
        "REPLAY_CAMPAIGN_SUMMARY "
        f"campaign_id={row[0]} "
        f"runs={row[1]} "
        f"success={row[2]} "
        f"failed={row[3]} "
        f"avg_duration_sec={row[4]} "
        f"symbols={row[5]} "
        f"strategies={row[6]}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
