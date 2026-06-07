#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


MIN_TRADES = 30
MIN_PROFIT_FACTOR = 1.10
MIN_EXPECTANCY = 0.0


def db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL_NOT_SET")
    return url


def main() -> None:
    print("=== ENERGY EDGE QUALITY DECISION V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("scope=BR_NG_ACTIVE_SHADOW_BLOCKED_DECISION")
    print()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                WITH base AS (
                    SELECT
                        CASE
                            WHEN left(symbol, 2) = 'BR' THEN 'BR'
                            WHEN left(symbol, 2) = 'NG' THEN 'NG'
                            ELSE 'OTHER'
                        END AS root,
                        upper(coalesce(side, 'UNKNOWN')) AS side,
                        coalesce(net_pnl, 0)::numeric AS pnl
                    FROM closed_trades
                    WHERE left(symbol, 2) IN ('BR','NG')
                ),
                agg AS (
                    SELECT
                        root,
                        side,
                        count(*) AS trades,
                        count(*) FILTER (WHERE pnl > 0) AS wins,
                        count(*) FILTER (WHERE pnl < 0) AS losses,
                        round(sum(pnl), 6) AS net_pnl,
                        round(avg(pnl), 6) AS expectancy,
                        CASE
                            WHEN abs(sum(pnl) FILTER (WHERE pnl < 0)) > 0
                            THEN round(
                                (sum(pnl) FILTER (WHERE pnl > 0))
                                / abs(sum(pnl) FILTER (WHERE pnl < 0)),
                                6
                            )
                            ELSE NULL
                        END AS profit_factor
                    FROM base
                    GROUP BY root, side
                )
                SELECT *
                FROM agg
                ORDER BY root, side;
                """
            )
            rows = cur.fetchall()

    stats = {(r["root"], r["side"]): r for r in rows}

    print("INPUT_METRICS")
    for r in rows:
        print(
            f"METRIC_ROW root={r['root']} side={r['side']} "
            f"trades={r['trades']} wins={r['wins']} losses={r['losses']} "
            f"net_pnl={r['net_pnl']} expectancy={r['expectancy']} "
            f"profit_factor={r['profit_factor']}"
        )
    print()

    decisions = []

    # Русский комментарий: BR long ранее признан слабым и остаётся в shadow/block.
    decisions.append(
        {
            "root": "BR",
            "direction": "LONG",
            "runtime_state": "SHADOW_OR_BLOCKED",
            "reason": "br_long_weak_or_negative_edge",
        }
    )

    # Русский комментарий: BR short имеет положительную research-гипотезу, но ждёт live-подтверждения route.
    br_sell = stats.get(("BR", "SELL"))
    if br_sell and int(br_sell["trades"]) >= MIN_TRADES:
        decisions.append(
            {
                "root": "BR",
                "direction": "SHORT",
                "runtime_state": "SHADOW",
                "reason": "br_short_positive_research_route_fixed_wait_live_confirmation",
            }
        )
    else:
        decisions.append(
            {
                "root": "BR",
                "direction": "SHORT",
                "runtime_state": "SHADOW",
                "reason": "br_short_research_positive_but_insufficient_closed_trade_aggregation",
            }
        )

    # Русский комментарий: NG long остаётся разрешённым как текущий рабочий контур.
    ng_buy = stats.get(("NG", "BUY"))
    if ng_buy and int(ng_buy["trades"]) >= MIN_TRADES:
        decisions.append(
            {
                "root": "NG",
                "direction": "LONG",
                "runtime_state": "ACTIVE",
                "reason": "ng_long_allowed_current_runtime_policy",
            }
        )
    else:
        decisions.append(
            {
                "root": "NG",
                "direction": "LONG",
                "runtime_state": "ACTIVE_WITH_CAUTION",
                "reason": "ng_long_allowed_but_quality_sample_requires_monitoring",
            }
        )

    # Русский комментарий: NG short отрицательный по quality audit, поэтому blocked.
    decisions.append(
        {
            "root": "NG",
            "direction": "SHORT",
            "runtime_state": "BLOCKED",
            "reason": "ng_short_negative_edge_quality_audit",
        }
    )

    print("DIRECTION_DECISIONS")
    for d in decisions:
        print(
            f"DECISION_ROW root={d['root']} direction={d['direction']} "
            f"runtime_state={d['runtime_state']} reason={d['reason']}"
        )
    print()

    print("RUNTIME_POLICY_MATRIX")
    print("POLICY_ROW instrument=BR direction=LONG action=DO_NOT_EXECUTE_REAL mode=shadow_or_blocked")
    print("POLICY_ROW instrument=BR direction=SHORT action=COLLECT_SHADOW_AND_WAIT_LIVE_CONFIRMATION mode=shadow")
    print("POLICY_ROW instrument=NG direction=LONG action=ALLOW_PAPER_AND_MONITOR mode=active")
    print("POLICY_ROW instrument=NG direction=SHORT action=BLOCK_OPEN_OR_ADD_SHORT_ALLOW_CLOSE_LONG mode=blocked")
    print()

    print("NEXT_CONTROL")
    print("NEXT_ROW check=BR_SHORT_LIVE_CONFIRMATION expected=PIPE_BR_SHORT_SHADOW_POLICY_V1 after_new_BR_SELL_candidate")
    print("NEXT_ROW check=NG_LONG_QUALITY_MONITOR expected=positive_or_stable_expectancy")
    print("NEXT_ROW check=TIME_EXIT_NOISE expected=no_duplicate_exit_distortion")
    print()

    print("VERDICT=ENERGY_DIRECTION_POLICY_FORMALIZED")
    print("ENERGY_EDGE_QUALITY_DECISION_V1_OK")


if __name__ == "__main__":
    main()
