from __future__ import annotations

import argparse
from finam_core.storage.postgres_logger import PostgresLogger


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--base-campaign", required=True)
    p.add_argument("--policy-campaign", required=True)
    return p.parse_args()


def load_stats(pg, campaign_id: str) -> dict:
    sql = """
    select
        count(*) as trades,
        round(coalesce(sum(net_pnl), 0)::numeric, 6) as net_pnl,
        round(coalesce(avg(net_pnl), 0)::numeric, 6) as expectancy,
        round(coalesce(avg(case when net_pnl > 0 then 1 else 0 end), 0)::numeric, 4) as winrate
    from closed_trades
    where coalesce(
        payload->>'replay_campaign_id',
        payload->'entry_payload'->>'replay_campaign_id',
        payload->'exit_payload'->>'replay_campaign_id',
        payload->'payload'->>'replay_campaign_id'
    ) = %s
      and trade_source = 'paper'
    """
    with pg._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (campaign_id,))
            row = cur.fetchone()

    return {
        "campaign_id": campaign_id,
        "trades": int(row[0] or 0),
        "net_pnl": float(row[1] or 0),
        "expectancy": float(row[2] or 0),
        "winrate": float(row[3] or 0),
    }


def main() -> int:
    args = parse_args()
    pg = PostgresLogger()

    base = load_stats(pg, args.base_campaign)
    policy = load_stats(pg, args.policy_campaign)

    delta_pnl = policy["net_pnl"] - base["net_pnl"]
    delta_expectancy = policy["expectancy"] - base["expectancy"]

    print(
        "АДАПТИВНЫЙ_РИСК_СРАВНЕНИЕ "
        f"base={base['campaign_id']} "
        f"policy={policy['campaign_id']} "
        f"base_trades={base['trades']} "
        f"policy_trades={policy['trades']} "
        f"base_net_pnl={base['net_pnl']:.6f} "
        f"policy_net_pnl={policy['net_pnl']:.6f} "
        f"delta_net_pnl={delta_pnl:.6f} "
        f"base_expectancy={base['expectancy']:.6f} "
        f"policy_expectancy={policy['expectancy']:.6f} "
        f"delta_expectancy={delta_expectancy:.6f} "
        f"base_winrate={base['winrate']:.4f} "
        f"policy_winrate={policy['winrate']:.4f}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
