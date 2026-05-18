from __future__ import annotations

import argparse

from finam_core.research.cross_sectional_selector import (
    CrossSectionalSelector,
    InstrumentPerformance,
)
from finam_core.storage.postgres_logger import PostgresLogger


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--campaign-pattern", required=True)
    p.add_argument("--top-n", type=int, default=2)
    p.add_argument("--min-trades", type=int, default=3)
    p.add_argument("--min-expectancy", type=float, default=0.0)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    pg = PostgresLogger()

    sql = """
    select
        symbol,
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
    group by symbol
    order by expectancy desc
    """

    with pg._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (args.campaign_pattern,))
            rows = cur.fetchall()

    items = [
        InstrumentPerformance(
            symbol=str(row[0]),
            trades=int(row[1]),
            net_pnl=float(row[2]),
            expectancy=float(row[3]),
            winrate=float(row[4]),
        )
        for row in rows
    ]

    selected = CrossSectionalSelector().select(
        items,
        top_n=args.top_n,
        min_trades=args.min_trades,
        min_expectancy=args.min_expectancy,
    )

    if not selected:
        print(
            f"КРОСС_СЕКЦИОННЫЙ_ОТБОР_ПУСТО pattern={args.campaign_pattern}",
            flush=True,
        )
        return 0

    item_by_symbol = {x.symbol: x for x in items}

    for x in selected:
        src = item_by_symbol[x.symbol]
        print(
            "КРОСС_СЕКЦИОННЫЙ_ОТБОР "
            f"pattern={args.campaign_pattern} "
            f"rank={x.rank} "
            f"инструмент={x.symbol} "
            f"сделок={src.trades} "
            f"net_pnl={src.net_pnl:.6f} "
            f"expectancy={src.expectancy:.6f} "
            f"winrate={src.winrate:.4f} "
            f"score={x.score:.6f} "
            f"решение={x.decision} "
            f"причина={x.reason}",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
