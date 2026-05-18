from __future__ import annotations

import argparse
from finam_core.storage.postgres_logger import PostgresLogger


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--base-campaign", required=True)
    p.add_argument("--limited-campaign", required=True)
    p.add_argument("--selective-campaign", required=True)
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
        payload->'payload'->>'replay_campaign_id',
        payload->'payload'->'entry_payload'->>'replay_campaign_id',
        payload->'payload'->'exit_payload'->>'replay_campaign_id'
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


def print_line(label: str, base: dict, current: dict) -> None:
    print(
        "АДАПТИВНЫЙ_РИСК_СРАВНЕНИЕ "
        f"режим={label} "
        f"campaign={current['campaign_id']} "
        f"trades={current['trades']} "
        f"net_pnl={current['net_pnl']:.6f} "
        f"expectancy={current['expectancy']:.6f} "
        f"winrate={current['winrate']:.4f} "
        f"delta_net_pnl={current['net_pnl'] - base['net_pnl']:.6f} "
        f"delta_expectancy={current['expectancy'] - base['expectancy']:.6f}",
        flush=True,
    )


def main() -> int:
    args = parse_args()
    pg = PostgresLogger()

    base = load_stats(pg, args.base_campaign)
    limited = load_stats(pg, args.limited_campaign)
    selective = load_stats(pg, args.selective_campaign)

    print_line("BASE", base, base)
    print_line("LIMITED", base, limited)
    print_line("SELECTIVE", base, selective)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
