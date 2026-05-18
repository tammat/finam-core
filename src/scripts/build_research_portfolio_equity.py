from __future__ import annotations

import argparse

from finam_core.research.cross_sectional_selector import CrossSectionalSelector, InstrumentPerformance
from finam_core.research.portfolio_research_allocator import (
    PortfolioResearchAllocator,
    ResearchInstrumentCandidate,
)
from finam_core.research.research_portfolio_metrics import ResearchPortfolioMetricsEngine
from finam_core.research.research_portfolio_equity import (
    PortfolioTrade,
    ResearchPortfolioEquityCurve,
)
from finam_core.storage.postgres_logger import PostgresLogger


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--campaign-pattern", required=True)
    p.add_argument("--top-n", type=int, default=2)
    p.add_argument("--min-trades", type=int, default=3)
    p.add_argument("--min-expectancy", type=float, default=0.0)
    p.add_argument("--max-symbol-weight", type=float, default=0.50)
    p.add_argument("--limit", type=int, default=20)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    pg = PostgresLogger()

    pattern = args.campaign_pattern

    perf_sql = """
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

    trade_sql = """
    select symbol, exit_ts, net_pnl
    from closed_trades
    where coalesce(
        payload->>'replay_campaign_id',
        payload->'payload'->>'replay_campaign_id'
    ) like %s
      and trade_source = 'paper'
      and symbol = any(%s)
    order by exit_ts, id
    """

    with pg._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(perf_sql, (pattern,))
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

    if not selected:
        print(f"ПОРТФЕЛЬНАЯ_EQUITY_ПУСТО pattern={pattern}", flush=True)
        return 0

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

    weights = {
        a.symbol: float(a.capital_weight)
        for a in allocations
        if a.capital_weight > 0
    }

    with pg._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(trade_sql, (pattern, list(weights.keys())))
            trade_rows = cur.fetchall()

    trades = [
        PortfolioTrade(
            symbol=str(r[0]),
            exit_ts=str(r[1]),
            net_pnl=float(r[2]),
            weight=weights[str(r[0])],
        )
        for r in trade_rows
    ]

    points = ResearchPortfolioEquityCurve().build(trades)

    if not points:
        print(f"ПОРТФЕЛЬНАЯ_EQUITY_ПУСТО pattern={pattern}", flush=True)
        return 0

    final = points[-1]
    max_dd = min(p.drawdown for p in points)
    metrics = ResearchPortfolioMetricsEngine().calculate(points)

    print(
        "ПОРТФЕЛЬНАЯ_EQUITY_ИТОГ "
        f"pattern={pattern} "
        f"точек={len(points)} "
        f"итоговая_прибыль={final.equity:.6f} "
        f"макс_просадка={max_dd:.6f} "
        f"инструменты={','.join(weights.keys())}",
        flush=True,
    )

    print(
        "ПОРТФЕЛЬНЫЕ_МЕТРИКИ "
        f"pattern={pattern} "
        f"точек={metrics.points} "
        f"net_pnl={metrics.net_pnl:.6f} "
        f"max_drawdown={metrics.max_drawdown:.6f} "
        f"expectancy={metrics.expectancy:.6f} "
        f"volatility={metrics.volatility:.6f} "
        f"sharpe_like={metrics.sharpe_like:.6f} "
        f"recovery_factor={metrics.recovery_factor:.6f} "
        f"winrate={metrics.winrate:.6f}",
        flush=True,
    )

    for p in points[-args.limit:]:
        print(
            "ПОРТФЕЛЬНАЯ_EQUITY "
            f"index={p.index} "
            f"ts={p.ts} "
            f"symbol={p.symbol} "
            f"weighted_pnl={p.weighted_pnl:.6f} "
            f"equity={p.equity:.6f} "
            f"drawdown={p.drawdown:.6f}",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
