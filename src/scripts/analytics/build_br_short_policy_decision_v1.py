#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


MIN_TRADES = 30
MIN_PF = 1.10
MIN_EXPECTANCY = 0.0


def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== BR SHORT POLICY DECISION V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("decision_scope=BR_OPEN_SHORT_POLICY")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                select
                    coalesce(strategy, 'UNKNOWN') as strategy,
                    count(*) as trades,
                    sum(entry_price - exit_price) as net_pnl,
                    avg(entry_price - exit_price) as expectancy,
                    avg(case when entry_price - exit_price > 0 then 1.0 else 0.0 end) as winrate,
                    sum(case when entry_price - exit_price > 0 then entry_price - exit_price else 0 end) as gross_profit,
                    abs(sum(case when entry_price - exit_price < 0 then entry_price - exit_price else 0 end)) as gross_loss
                from (
                    select
                        s.id,
                        s.symbol,
                        s.strategy,
                        coalesce(
                            nullif(s.entry_price, 0),
                            nullif((s.payload->>'entry_price')::numeric, 0),
                            nullif((s.payload->>'price')::numeric, 0)
                        ) as entry_price,
                        b.close as exit_price
                    from signals s
                    join lateral (
                        select mb.close
                        from market_bars mb
                        where mb.symbol = s.symbol
                          and mb.timeframe = 'M5'
                          and mb.ts > s.ts
                        order by mb.ts
                        offset 23 limit 1
                    ) b on true
                    where s.symbol in ('BRM6@RTSX','BRN6@RTSX')
                      and s.side = 'SELL'
                      and coalesce(s.status,'') in ('risk_accepted','ACCEPTED','NEW')
                      and coalesce(s.strategy,'UNKNOWN') in (
                          'BR_CONSERVATIVE_BREAKOUT',
                          'BR_CONSERVATIVE_BREAKOUT_M5',
                          'HISTORICAL_BREAKOUT_V1'
                      )
                ) x
                where entry_price is not null
                  and exit_price is not null
                group by strategy
                order by strategy;
                """
            )
            rows = cur.fetchall()

    print("POLICY_INPUTS")
    print(f"min_trades={MIN_TRADES}")
    print(f"min_profit_factor={MIN_PF}")
    print(f"min_expectancy={MIN_EXPECTANCY}")
    print("exit_policy=2h_shadow_short")
    print()

    allow = []
    block = []

    print("STRATEGY_DECISIONS")
    for r in rows:
        strategy = str(r["strategy"])
        trades = int(r["trades"] or 0)
        net = float(r["net_pnl"] or 0.0)
        expectancy = float(r["expectancy"] or 0.0)
        winrate = float(r["winrate"] or 0.0)
        gp = float(r["gross_profit"] or 0.0)
        gl = float(r["gross_loss"] or 0.0)
        pf = gp / gl if gl > 0 else None

        passed = (
            trades >= MIN_TRADES
            and net > 0
            and expectancy > MIN_EXPECTANCY
            and (pf is None or pf >= MIN_PF)
        )

        # Русский комментарий: short разрешаем только канонической BR-стратегии.
        if strategy != "BR_CONSERVATIVE_BREAKOUT":
            passed = False
            reason = "block_non_canonical_br_strategy"
        elif passed:
            reason = "allow_canonical_br_short_edge_validated"
        else:
            reason = "block_edge_threshold_not_passed"

        target = allow if passed else block
        target.append(strategy)

        print(
            "STRATEGY_DECISION_ROW "
            f"strategy={strategy} trades={trades} "
            f"net_pnl={net:.8f} expectancy={expectancy:.8f} "
            f"winrate={winrate:.4f} "
            f"profit_factor={pf if pf is not None else 'None'} "
            f"allow_open_short={int(passed)} reason={reason}"
        )

    print()
    print("POLICY_DECISION")
    print("symbol_root=BR")
    print("side=SELL")
    print("position_condition=position<=0")
    print(f"allow_strategies={','.join(allow) if allow else 'NONE'}")
    print(f"block_strategies={','.join(block) if block else 'NONE'}")
    print("execution_mode_initial=shadow")
    print("runtime_change_now=0")
    print()

    if "BR_CONSERVATIVE_BREAKOUT" in allow:
        print("VERDICT=ALLOW_BR_CANONICAL_SHORT_IN_SHADOW_ONLY")
    else:
        print("VERDICT=DO_NOT_ENABLE_BR_SHORT")


if __name__ == "__main__":
    main()
