#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

from finam_core.research.open_short_policy_v1 import OpenShortPolicyV1
from finam_core.signals.intent_semantics_v2 import classify_intent_semantics_v2


def main() -> None:
    dsn = os.environ["DATABASE_URL"]
    policy = OpenShortPolicyV1(mode=os.getenv("BR_OPEN_SHORT_RESEARCH_MODE", "shadow"))

    print("=== BR OPEN SHORT POLICY RESEARCH V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("policy_mode=shadow")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                select
                    id, symbol, side, qty, price, ts,
                    coalesce(strategy, 'UNKNOWN') as strategy,
                    coalesce(timeframe, 'UNKNOWN') as timeframe,
                    coalesce(origin, 'UNKNOWN') as origin,
                    coalesce(trade_source, 'UNKNOWN') as trade_source
                from trades
                where symbol in ('BRM6@RTSX','BRN6@RTSX')
                  and trade_source='paper'
                  and coalesce(is_invalid,false)=false
                order by symbol, ts, id;
            """)
            rows = cur.fetchall()

    positions: dict[str, float] = {}
    candidates = []
    action_counts: dict[str, int] = {}
    policy_counts: dict[str, int] = {}

    for r in rows:
        symbol = str(r["symbol"])
        strategy = str(r["strategy"])
        pos_before = float(positions.get(symbol, 0.0))
        qty = float(r["qty"] or 0.0)

        d = classify_intent_semantics_v2(
            side=str(r["side"]),
            current_position=pos_before,
            requested_qty=qty,
        )

        action = d.action.value
        action_counts[action] = action_counts.get(action, 0) + 1

        decision = policy.evaluate(symbol=symbol, strategy=strategy, action=action)
        policy_counts[decision.reason] = policy_counts.get(decision.reason, 0) + 1

        if action == "OPEN_SHORT":
            candidates.append((r, pos_before, d, decision))

        positions[symbol] = float(d.resulting_position)

    print("OBSERVED_ACTIONS")
    for action, rows_count in sorted(action_counts.items()):
        print(f"ACTION_ROW action={action} rows={rows_count}")
    print()

    print("POLICY_DECISIONS_ON_OBSERVED_FLOW")
    for reason, rows_count in sorted(policy_counts.items()):
        print(f"POLICY_ROW reason={reason} rows={rows_count}")
    print()

    print("OBSERVED_OPEN_SHORT_CANDIDATES")
    print(f"OPEN_SHORT_CANDIDATES={len(candidates)}")
    for r, pos_before, d, decision in candidates[:50]:
        print(
            "OPEN_SHORT_CANDIDATE_ROW "
            f"id={r['id']} ts={r['ts']} symbol={r['symbol']} side={r['side']} "
            f"qty={r['qty']} price={r['price']} strategy={r['strategy']} "
            f"position_before={pos_before} action={d.action.value} "
            f"allowed={int(decision.allowed)} reason={decision.reason}"
        )
    print()

    print("HYPOTHETICAL_ENABLEMENT")
    print("HYPOTHESIS=allow_BR_SELL_as_OPEN_SHORT_only_when_position_is_flat_or_short")
    print("CURRENT_RESULT=historical_BR_flow_has_no_flat_SELL_events")
    print("REQUIRED_NEXT_TEST=generate_short_entries_from_strategy_signal_layer_not_trade_layer")
    print()

    if len(candidates) == 0:
        print("VERDICT=NO_HISTORICAL_OPEN_SHORT_CANDIDATES_IN_TRADES")
    else:
        print("VERDICT=OPEN_SHORT_POLICY_CANDIDATES_FOUND")


if __name__ == "__main__":
    main()
