from __future__ import annotations

import argparse

from finam_core.research.cross_sectional_selector import CrossSectionalSelector, InstrumentPerformance
from finam_core.research.portfolio_research_allocator import (
    PortfolioResearchAllocator,
    ResearchInstrumentCandidate,
)
from finam_core.storage.postgres_logger import PostgresLogger


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--campaign-pattern", required=True)
    p.add_argument("--top-n", type=int, default=2)
    p.add_argument("--min-trades", type=int, default=3)
    p.add_argument("--min-expectancy", type=float, default=0.0)
    p.add_argument("--max-symbol-weight", type=float, default=0.50)
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
    """

    with pg._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (args.campaign_pattern,))
            rows = cur.fetchall()

    performances = [
        InstrumentPerformance(
            symbol=str(r[0]),
            trades=int(r[1]),
            net_pnl=float(r[2]),
            expectancy=float(r[3]),
            winrate=float(r[4]),
        )
        for r in rows
    ]

    selected = CrossSectionalSelector().select(
        performances,
        top_n=args.top_n,
        min_trades=args.min_trades,
        min_expectancy=args.min_expectancy,
    )

    by_symbol = {p.symbol: p for p in performances}

    candidates = [
        ResearchInstrumentCandidate(
            symbol=s.symbol,
            trades=by_symbol[s.symbol].trades,
            net_pnl=by_symbol[s.symbol].net_pnl,
            expectancy=by_symbol[s.symbol].expectancy,
            winrate=by_symbol[s.symbol].winrate,
            score=s.score,
        )
        for s in selected
    ]

    allocations = PortfolioResearchAllocator().allocate(
        candidates,
        max_symbol_weight=args.max_symbol_weight,
        min_trades=args.min_trades,
        min_expectancy=args.min_expectancy,
    )

    if not allocations:
        print(f"ИССЛЕДОВАТЕЛЬСКИЙ_ПОРТФЕЛЬ_ПУСТО pattern={args.campaign_pattern}", flush=True)
        return 0

    for a in allocations:
        print(
            "ИССЛЕДОВАТЕЛЬСКИЙ_ПОРТФЕЛЬ "
            f"pattern={args.campaign_pattern} "
            f"инструмент={a.symbol} "
            f"вес_капитала={a.capital_weight:.6f} "
            f"вес_риска={a.risk_weight:.6f} "
            f"решение={a.decision} "
            f"причина={a.reason}",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
