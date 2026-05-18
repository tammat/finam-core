from __future__ import annotations

import argparse

from finam_core.research.regime_policy_repository import RegimePolicyRepository
from finam_core.research.regime_risk_policy import RegimePerformance, RegimeRiskPolicy
from finam_core.storage.postgres_logger import PostgresLogger


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--campaign-pattern", required=True)
    p.add_argument("--min-trades", type=int, default=5)
    p.add_argument("--min-expectancy", type=float, default=0.0)
    p.add_argument("--policy-id", default="")
    p.add_argument("--save", action="store_true")
    p.add_argument("--min-winrate-to-allow", type=float, default=0.55)
    p.add_argument("--min-winrate-to-limit", type=float, default=0.45)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    sql = """
    with base as (
        select
            coalesce(
                payload->>'research_regime',
                payload->'entry_payload'->>'research_regime',
                payload->'exit_payload'->>'research_regime',
                payload->'payload'->>'research_regime',
                payload->'payload'->'entry_payload'->>'research_regime',
                payload->'payload'->'exit_payload'->>'research_regime',
                'UNKNOWN'
            ) as regime,
            coalesce(
                payload->>'research_trend',
                payload->'entry_payload'->>'research_trend',
                payload->'exit_payload'->>'research_trend',
                payload->'payload'->>'research_trend',
                payload->'payload'->'entry_payload'->>'research_trend',
                payload->'payload'->'exit_payload'->>'research_trend',
                'UNKNOWN'
            ) as trend,
            coalesce(
                payload->>'research_volatility',
                payload->'entry_payload'->>'research_volatility',
                payload->'exit_payload'->>'research_volatility',
                payload->'payload'->>'research_volatility',
                payload->'payload'->'entry_payload'->>'research_volatility',
                payload->'payload'->'exit_payload'->>'research_volatility',
                'UNKNOWN'
            ) as volatility,
            net_pnl
        from closed_trades
        where coalesce(
            payload->>'replay_campaign_id',
            payload->'entry_payload'->>'replay_campaign_id',
            payload->'exit_payload'->>'replay_campaign_id',
            payload->'payload'->>'replay_campaign_id',
            payload->'payload'->'entry_payload'->>'replay_campaign_id',
            payload->'payload'->'exit_payload'->>'replay_campaign_id'
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
        round(avg(case when net_pnl > 0 then 1 else 0 end)::numeric, 4) as winrate
    from base
    group by regime, trend, volatility
    order by expectancy desc, net_pnl desc
    """

    pg = PostgresLogger()

    with pg._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (args.campaign_pattern,))
            rows = cur.fetchall()

    items = [
        RegimePerformance(
            regime=str(r[0]),
            trend=str(r[1]),
            volatility=str(r[2]),
            trades=int(r[3]),
            net_pnl=float(r[4]),
            expectancy=float(r[5]),
            winrate=float(r[6]),
        )
        for r in rows
    ]

    decisions = RegimeRiskPolicy().decide(
        items,
        min_trades=args.min_trades,
        min_expectancy=args.min_expectancy,
        min_winrate_to_allow=args.min_winrate_to_allow,
        min_winrate_to_limit=args.min_winrate_to_limit,
    )

    if args.save and decisions:
        policy_id = args.policy_id or args.campaign_pattern.replace("%", "ALL").replace("*", "ALL")
        with pg._connect() as conn:
            saved = RegimePolicyRepository(conn).save_policy(
                policy_id=policy_id,
                campaign_pattern=args.campaign_pattern,
                decisions=decisions,
            )
        print(
            "ПОЛИТИКА_РЕЖИМОВ_СОХРАНЕНА "
            f"policy_id={policy_id} rows={saved}",
            flush=True,
        )

    if not decisions:
        print(f"ПОЛИТИКА_РЕЖИМОВ_ПУСТО pattern={args.campaign_pattern}", flush=True)
        return 0

    for d in decisions:
        print(
            "ПОЛИТИКА_РЕЖИМОВ "
            f"pattern={args.campaign_pattern} "
            f"regime={d.regime} "
            f"trend={d.trend} "
            f"volatility={d.volatility} "
            f"решение={d.decision} "
            f"множитель_риска={d.risk_multiplier:.2f} "
            f"причина={d.reason}",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
