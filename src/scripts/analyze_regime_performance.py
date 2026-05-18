from __future__ import annotations

import argparse

from finam_core.storage.postgres_logger import PostgresLogger


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--campaign-pattern", required=True)
    p.add_argument("--limit", type=int, default=50)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    sql = """
    with base as (
        select
            coalesce(payload->>'research_regime', payload->'payload'->>'research_regime', 'UNKNOWN') as regime,
            coalesce(payload->>'research_trend', payload->'payload'->>'research_trend', 'UNKNOWN') as trend,
            coalesce(payload->>'research_volatility', payload->'payload'->>'research_volatility', 'UNKNOWN') as volatility,
            net_pnl
        from closed_trades
        where coalesce(
            payload->>'replay_campaign_id',
            payload->'payload'->>'replay_campaign_id'
        ) like %s
          and trade_source = 'paper'
    )
    select
        regime,
        trend,
        volatility,
        count(*) as trades,
        round(sum(net_pnl)::numeric, 6) as net_pnl,
        round(avg(net_pnl)::numeric, 6) as expectancy,
        round(avg(case when net_pnl > 0 then 1 else 0 end)::numeric, 4) as winrate,
        round(min(net_pnl)::numeric, 6) as worst_trade,
        round(max(net_pnl)::numeric, 6) as best_trade
    from base
    group by regime, trend, volatility
    order by expectancy desc, net_pnl desc
    limit %s
    """

    pg = PostgresLogger()

    with pg._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (args.campaign_pattern, args.limit))
            rows = cur.fetchall()

    if not rows:
        print(
            f"АНАЛИТИКА_РЕЖИМОВ_ПУСТО pattern={args.campaign_pattern}",
            flush=True,
        )
        return 0

    for row in rows:
        print(
            "АНАЛИТИКА_РЕЖИМОВ "
            f"pattern={args.campaign_pattern} "
            f"regime={row[0]} "
            f"trend={row[1]} "
            f"volatility={row[2]} "
            f"trades={row[3]} "
            f"net_pnl={float(row[4]):.6f} "
            f"expectancy={float(row[5]):.6f} "
            f"winrate={float(row[6]):.4f} "
            f"worst_trade={float(row[7]):.6f} "
            f"best_trade={float(row[8]):.6f}",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
