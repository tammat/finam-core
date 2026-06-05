#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


DDL = """
create table if not exists research_regime_guard_candidates (
    id bigserial primary key,
    scope text not null,
    regime_key text not null,

    classification text not null,
    reason text not null,

    trades integer not null,
    wins integer not null,
    losses integer not null,
    winrate double precision not null,
    net_pnl double precision not null,
    expectancy double precision not null,
    profit_factor double precision,

    source text not null default 'regime_guard_candidate_v1',
    generated_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    unique(scope, regime_key, source)
);

create index if not exists idx_research_regime_guard_candidates_class
    on research_regime_guard_candidates(classification);

create index if not exists idx_research_regime_guard_candidates_scope
    on research_regime_guard_candidates(scope, regime_key);
"""


def conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def classify(trades: int, net_pnl: float, expectancy: float, profit_factor):
    if trades < 5:
        return "INSUFFICIENT_SAMPLE", "sample_lt_5"

    pf = None if profit_factor is None else float(profit_factor)

    if net_pnl < 0 and expectancy < 0 and (pf is None or pf < 0.70):
        return "BLOCK_CANDIDATE", "negative_expectancy_and_low_pf"

    if net_pnl < 0 or expectancy < 0:
        return "WATCH_CANDIDATE", "negative_or_weak_expectancy"

    if net_pnl > 0 and expectancy > 0 and (pf is None or pf >= 1.20):
        return "ALLOW_CANDIDATE", "positive_expectancy"

    return "WATCH_CANDIDATE", "neutral_or_unclear"


def metrics(values):
    trades = len(values)
    wins = sum(1 for v in values if v > 0)
    losses = sum(1 for v in values if v < 0)
    net_pnl = sum(values)
    winrate = wins / trades if trades else 0.0
    expectancy = net_pnl / trades if trades else 0.0
    gross_profit = sum(v for v in values if v > 0)
    gross_loss = abs(sum(v for v in values if v < 0))
    profit_factor = None if gross_loss == 0 else gross_profit / gross_loss
    return trades, wins, losses, winrate, net_pnl, expectancy, profit_factor


def main():
    sql = """
        with trades_base as (
            select
                id,
                symbol as trade_symbol,
                strategy,
                side,
                timeframe,
                net_pnl,
                coalesce(
                    (payload->'entry_payload'->>'ts')::timestamptz,
                    (payload->>'entry_ts')::timestamptz,
                    opened_at,
                    created_at
                ) as entry_ts
            from closed_trades
            where source = 'closed_trade_engine_v1_1'
              and trade_source = 'paper'
        ),
        feature_base as (
            select
                symbol,
                ts,
                case
                    when expansion_flag then 'EXPANSION'
                    when compression_flag then 'COMPRESSION'
                    else 'MIXED'
                end as regime
            from research_feature_store
            where timeframe = 'M5'
              and symbol in ('BRN6@RTSX','NGN6@RTSX','USDRUBF@RTSX','BTCUSD','ETHUSD')
        )
        select
            t.net_pnl,
            coalesce(br.regime, 'NA') as br_regime,
            coalesce(ng.regime, 'NA') as ng_regime,
            coalesce(usd.regime, 'NA') as usd_regime,
            coalesce(btc.regime, 'NA') as btc_regime,
            coalesce(eth.regime, 'NA') as eth_regime
        from trades_base t
        left join feature_base br
          on br.symbol='BRN6@RTSX'
         and br.ts = date_trunc('minute', t.entry_ts)
        left join feature_base ng
          on ng.symbol='NGN6@RTSX'
         and ng.ts = date_trunc('minute', t.entry_ts)
        left join feature_base usd
          on usd.symbol='USDRUBF@RTSX'
         and usd.ts = date_trunc('minute', t.entry_ts)
        left join feature_base btc
          on btc.symbol='BTCUSD'
         and btc.ts = date_trunc('minute', t.entry_ts)
        left join feature_base eth
          on eth.symbol='ETHUSD'
         and eth.ts = date_trunc('minute', t.entry_ts);
    """

    with conn() as c:
        with c.cursor() as cur:
            cur.execute(DDL)
            cur.execute(sql)
            rows = cur.fetchall()

    groups = {}

    for net_pnl, br, ng, usd, btc, eth in rows:
        net = float(net_pnl or 0)

        energy_key = f"BR={br}|NG={ng}|USD={usd}"
        crypto_key = f"BTC={btc}|ETH={eth}"
        full_key = f"{energy_key}|{crypto_key}"

        groups.setdefault(("ENERGY_USD", energy_key), []).append(net)
        groups.setdefault(("CRYPTO", crypto_key), []).append(net)
        groups.setdefault(("FULL", full_key), []).append(net)

    print("=== MATERIALIZE REGIME GUARD CANDIDATE V1 ===")

    written = 0

    upsert = """
        insert into research_regime_guard_candidates (
            scope,
            regime_key,
            classification,
            reason,
            trades,
            wins,
            losses,
            winrate,
            net_pnl,
            expectancy,
            profit_factor,
            source,
            updated_at
        )
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'regime_guard_candidate_v1',now())
        on conflict (scope, regime_key, source)
        do update set
            classification=excluded.classification,
            reason=excluded.reason,
            trades=excluded.trades,
            wins=excluded.wins,
            losses=excluded.losses,
            winrate=excluded.winrate,
            net_pnl=excluded.net_pnl,
            expectancy=excluded.expectancy,
            profit_factor=excluded.profit_factor,
            updated_at=now()
    """

    with conn() as c:
        with c.cursor() as cur:
            for (scope, key), values in sorted(groups.items()):
                trades, wins, losses, winrate, net_pnl, expectancy, pf = metrics(values)
                classification, reason = classify(trades, net_pnl, expectancy, pf)

                cur.execute(
                    upsert,
                    (
                        scope,
                        key,
                        classification,
                        reason,
                        trades,
                        wins,
                        losses,
                        winrate,
                        net_pnl,
                        expectancy,
                        pf,
                    ),
                )

                written += 1

                print(
                    f"CANDIDATE_ROW scope={scope} key={key} "
                    f"classification={classification} reason={reason} "
                    f"trades={trades} wins={wins} losses={losses} "
                    f"winrate={winrate:.4f} net_pnl={net_pnl:.8f} "
                    f"expectancy={expectancy:.8f} "
                    f"profit_factor={'None' if pf is None else f'{pf:.8f}'}"
                )

    print()
    print(f"ROWS_WRITTEN={written}")
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
