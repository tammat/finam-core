#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

from finam_core.governance.time_exit_governance_v1 import TimeExitGovernanceV1


SOURCE = "closed_trade_engine_v1_1"


def db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL_NOT_SET")
    return url


def pf(pos_sum: float, neg_sum: float):
    if neg_sum < 0:
        return pos_sum / abs(neg_sum)
    return None


def metrics(rows):
    trades = len(rows)
    wins = sum(1 for r in rows if r["net_pnl"] > 0)
    losses = sum(1 for r in rows if r["net_pnl"] < 0)
    net = sum(float(r["net_pnl"]) for r in rows)
    pos = sum(float(r["net_pnl"]) for r in rows if r["net_pnl"] > 0)
    neg = sum(float(r["net_pnl"]) for r in rows if r["net_pnl"] < 0)
    return {
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "net_pnl": net,
        "expectancy": net / trades if trades else 0.0,
        "profit_factor": pf(pos, neg),
    }


def fmt(value):
    if value is None:
        return "None"
    return f"{float(value):.6f}"


def main() -> None:
    print("=== TIME EXIT GOVERNANCE EFFECTIVENESS V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"source={SOURCE}")
    print()

    governance = TimeExitGovernanceV1(mode="shadow")

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    id,
                    symbol,
                    coalesce(root_symbol,
                        CASE
                            WHEN left(symbol, 2) = 'BR' THEN 'BR'
                            WHEN left(symbol, 2) = 'NG' THEN 'NG'
                            ELSE 'OTHER'
                        END
                    ) AS root,
                    upper(side) AS side,
                    net_pnl,
                    payload,
                    exit_ts,
                    closed_at,
                    created_at
                FROM closed_trades
                WHERE source = %s
                  AND left(symbol, 2) IN ('BR','NG')
                ORDER BY root, symbol, coalesce(exit_ts, closed_at, created_at), id
                """,
                (SOURCE,),
            )
            rows = cur.fetchall()

    enriched = []
    for r in rows:
        payload = r["payload"] or {}
        exit_reason = (
            payload.get("exit_reason")
            or payload.get("reason")
            or "UNKNOWN"
        )

        decision = governance.evaluate(
            root_symbol=str(r["root"]),
            side=str(r["side"]),
            unrealized_pnl=float(r["net_pnl"] or 0.0),
            reason=str(exit_reason),
        )

        item = dict(r)
        item["exit_reason"] = str(exit_reason)
        item["gov_allowed"] = bool(decision.allowed)
        item["gov_action"] = decision.action
        item["gov_reason"] = decision.reason
        enriched.append(item)

    print("GOVERNANCE_ACTION_SUMMARY")
    action_groups = {}
    for r in enriched:
        key = (r["root"], r["gov_action"], r["gov_reason"])
        action_groups.setdefault(key, []).append(r)

    for (root, action, reason), group in sorted(action_groups.items()):
        m = metrics(group)
        print(
            f"ACTION_ROW root={root} action={action} reason={reason} "
            f"trades={m['trades']} net_pnl={fmt(m['net_pnl'])} "
            f"expectancy={fmt(m['expectancy'])} profit_factor={fmt(m['profit_factor'])}"
        )
    print()

    print("ROOT_EFFECTIVENESS")
    roots = sorted(set(r["root"] for r in enriched))
    for root in roots:
        actual_rows = [r for r in enriched if r["root"] == root]
        governed_rows = [
            r for r in actual_rows
            if r["gov_action"] != "SHADOW_BLOCK"
        ]
        blocked_rows = [
            r for r in actual_rows
            if r["gov_action"] == "SHADOW_BLOCK"
        ]

        actual = metrics(actual_rows)
        governed = metrics(governed_rows)
        blocked = metrics(blocked_rows)

        delta = governed["net_pnl"] - actual["net_pnl"]
        exp_delta = governed["expectancy"] - actual["expectancy"]

        if blocked["trades"] == 0:
            verdict = "NO_GOVERNANCE_CANDIDATES"
        elif delta > 0 and exp_delta > 0:
            verdict = "ENABLE_CANDIDATE"
        else:
            verdict = "KEEP_SHADOW"

        print(
            f"ROOT_ROW root={root} "
            f"actual_trades={actual['trades']} actual_net_pnl={fmt(actual['net_pnl'])} "
            f"actual_expectancy={fmt(actual['expectancy'])} actual_pf={fmt(actual['profit_factor'])} "
            f"governed_trades={governed['trades']} governed_net_pnl={fmt(governed['net_pnl'])} "
            f"governed_expectancy={fmt(governed['expectancy'])} governed_pf={fmt(governed['profit_factor'])} "
            f"blocked_trades={blocked['trades']} blocked_net_pnl={fmt(blocked['net_pnl'])} "
            f"delta_pnl={fmt(delta)} delta_expectancy={fmt(exp_delta)} "
            f"verdict={verdict}"
        )
    print()

    print("BLOCKED_SAMPLE")
    sample = [r for r in enriched if r["gov_action"] == "SHADOW_BLOCK"][:30]
    if not sample:
        print("NO_BLOCKED_SAMPLE")
    for r in sample:
        print(
            f"BLOCKED_ROW id={r['id']} root={r['root']} symbol={r['symbol']} "
            f"side={r['side']} exit_reason={r['exit_reason']} "
            f"net_pnl={fmt(r['net_pnl'])} gov_reason={r['gov_reason']}"
        )
    print()

    print("VERDICT=TIME_EXIT_GOVERNANCE_EFFECTIVENESS_RECORDED")
    print("TIME_EXIT_GOVERNANCE_EFFECTIVENESS_V1_OK")


if __name__ == "__main__":
    main()
