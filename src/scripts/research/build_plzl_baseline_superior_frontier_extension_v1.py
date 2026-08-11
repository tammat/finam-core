from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.entry_exit_optimizer import (
    Bar,
    Variant,
    candidate_statistical_gate,
    negative_control_check,
    simulate_variant,
)

from scripts.analytics.build_entry_exit_optimizer_v1 import (
    SUPPORTED,
    SHADOW_HORIZON_BARS,
    atr_at_entry,
    entry_context_at_signal,
    execution_economics,
    placebo_entry_offsets,
    symbol_group,
    timeframe_delta,
)


TARGET_STRATEGY = "MEAN_REVERSION_EQUITY"
TARGET_GROUP = "PLZL"
TARGET_SIDE = "SHORT"


def main() -> int:
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.set_session(readonly=True, autocommit=False)

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    s.id,
                    s.signal_id,
                    s.strategy,
                    s.symbol,
                    s.side,
                    s.entry_price,
                    s.stop_loss,
                    s.take_profit,
                    coalesce(s.ts,s.created_at) AS entry_ts,
                    coalesce(c.commission,0) AS commission,
                    coalesce(s.qty,c.qty,1) AS qty,
                    coalesce(
                        s.payload->'context'->>'regime_trend',
                        s.payload->'context'->>'regime',
                        s.regime,
                        'UNKNOWN'
                    ) AS regime
                FROM signals s
                LEFT JOIN LATERAL (
                    SELECT
                        ct.id,
                        ct.commission,
                        ct.qty
                    FROM closed_trades ct
                    WHERE ct.signal_id=s.signal_id
                      AND ct.trade_source='paper'
                      AND ct.payload->'pnl_units'->>'version'
                          ='PNL_UNITS_V2_RUB'
                    ORDER BY coalesce(
                        ct.entry_ts,
                        ct.opened_at,
                        ct.created_at
                    )
                    LIMIT 1
                ) c ON true
                WHERE coalesce(
                    s.payload->'context'->>'cohort',
                    s.payload->>'portfolio_scope',
                    ''
                ) LIKE 'FRESH_V5%%'
                  AND s.status IN ('FILLED','RISK_REJECTED')
                  AND s.strategy=%s
                  AND coalesce(s.ts,s.created_at) IS NOT NULL
                  AND s.entry_price IS NOT NULL
                  AND s.entry_price>0
                ORDER BY coalesce(s.ts,s.created_at),s.id
                """,
                (TARGET_STRATEGY,),
            )

            independent = set()
            bundles = []

            for trade in cur.fetchall():
                side = (
                    "LONG"
                    if trade["side"] in {"LONG", "BUY"}
                    else "SHORT"
                )

                group = symbol_group(
                    trade["strategy"],
                    trade["symbol"],
                )

                if group != TARGET_GROUP or side != TARGET_SIDE:
                    continue

                bucket = trade["entry_ts"].replace(
                    minute=(trade["entry_ts"].minute // 30) * 30,
                    second=0,
                    microsecond=0,
                )

                key = (
                    trade["strategy"],
                    group,
                    side,
                    bucket,
                )

                if key in independent:
                    continue

                atr = atr_at_entry(
                    cur,
                    trade["symbol"],
                    SUPPORTED[trade["strategy"]],
                    trade["entry_ts"],
                )

                if not atr:
                    continue

                economics = execution_economics(cur, trade)

                if not economics:
                    continue

                completed_cutoff = (
                    datetime.now(trade["entry_ts"].tzinfo)
                    - timeframe_delta(
                        SUPPORTED[trade["strategy"]]
                    )
                )

                cur.execute(
                    """
                    SELECT
                        open::float8,
                        high::float8,
                        low::float8,
                        close::float8
                    FROM market_bars
                    WHERE symbol=%s
                      AND timeframe=%s
                      AND ts>%s
                      AND ts<=%s
                    ORDER BY ts
                    LIMIT %s
                    """,
                    (
                        trade["symbol"],
                        SUPPORTED[trade["strategy"]],
                        trade["entry_ts"],
                        completed_cutoff,
                        SHADOW_HORIZON_BARS[
                            trade["strategy"]
                        ],
                    ),
                )

                bars = [
                    Bar(
                        float(row["high"]),
                        float(row["low"]),
                        float(row["close"]),
                        float(row["open"]),
                    )
                    for row in cur.fetchall()
                ]

                if not bars:
                    continue

                horizon_complete = (
                    len(bars)
                    == SHADOW_HORIZON_BARS[
                        trade["strategy"]
                    ]
                )

                independent.add(key)

                entry_context = entry_context_at_signal(
                    cur,
                    trade,
                    SUPPORTED[trade["strategy"]],
                    float(atr),
                    economics["roundtrip_cost_price"],
                    side,
                )

                bundles.append(
                    (
                        trade,
                        float(atr),
                        bars,
                        economics,
                        horizon_complete,
                        entry_context,
                    )
                )

        grid = [
            (
                f"PLZL_FRONTIER_S{stop:.1f}_RM{reward_mult:.1f}",
                stop,
                round(stop * reward_mult, 6),
            )
            for stop in (1.4, 1.5, 1.6, 1.7, 1.8)
            for reward_mult in (1.2, 1.3, 1.4)
        ]

        results = []

        for grid_index, (code, stop_atr, take_atr) in enumerate(grid):
            variant = Variant(
                code=code,
                entry_mode="IMMEDIATE",
                stop_atr=stop_atr,
                take_atr=take_atr,
                policy_code="PLZL_FRONTIER_RESEARCH_V1",
                shadow_only=True,
            )

            rows = []

            for (
                trade,
                atr,
                bars,
                economics,
                horizon_complete,
                entry_context,
            ) in bundles:
                if not horizon_complete:
                    continue

                side = TARGET_SIDE
                direction = 1.0 if side == "LONG" else -1.0

                risk = atr * variant.stop_atr
                if risk <= 0:
                    continue

                signal_stop = float(trade.get("stop_loss") or 0.0)
                signal_take = float(trade.get("take_profit") or 0.0)

                baseline_stop_atr = (
                    abs(float(trade["entry_price"]) - signal_stop) / atr
                    if signal_stop > 0
                    else variant.stop_atr
                )

                baseline_take_atr = (
                    direction
                    * (signal_take - float(trade["entry_price"]))
                    / atr
                    if signal_take > 0
                    else variant.take_atr
                )

                if baseline_stop_atr <= 0 or baseline_take_atr <= 0:
                    baseline_stop_atr = variant.stop_atr
                    baseline_take_atr = variant.take_atr

                baseline = simulate_variant(
                    signal_price=float(trade["entry_price"]),
                    side=side,
                    atr=atr,
                    bars=bars,
                    variant=Variant(
                        "CURRENT_PAPER",
                        "IMMEDIATE",
                        baseline_stop_atr,
                        baseline_take_atr,
                    ),
                    entry_context=entry_context,
                    roundtrip_cost_price=economics[
                        "roundtrip_cost_price"
                    ],
                    tick_size=economics["tick_size"],
                    stop_slippage_ticks=float(
                        os.getenv(
                            "SHADOW_STOP_SLIPPAGE_TICKS",
                            "1",
                        )
                    ),
                )

                baseline_net_move = (
                    direction
                    * (
                        float(baseline.exit_price)
                        - float(trade["entry_price"])
                    )
                    - economics["roundtrip_cost_price"]
                )

                actual_r = baseline_net_move / risk

                outcome = simulate_variant(
                    signal_price=float(trade["entry_price"]),
                    side=side,
                    atr=atr,
                    bars=bars,
                    variant=variant,
                    entry_context=entry_context,
                    roundtrip_cost_price=economics[
                        "roundtrip_cost_price"
                    ],
                    tick_size=economics["tick_size"],
                    stop_slippage_ticks=float(
                        os.getenv(
                            "SHADOW_STOP_SLIPPAGE_TICKS",
                            "1",
                        )
                    ),
                )

                roundtrip_cost_r = (
                    economics["roundtrip_cost_price"] / risk
                )

                placebo_offsets = placebo_entry_offsets(
                    bars_count=len(bars),
                    source_id=int(trade["id"]),
                    candidate_code=variant.code,
                    candidate_delay_bars=int(
                        outcome.entry_delay_bars or 0
                    ),
                    samples=int(
                        os.getenv(
                            "SHADOW_PLACEBO_TIME_SHIFTS",
                            "20",
                        )
                    ),
                )

                placebo_results = [
                    simulate_variant(
                        signal_price=float(
                            bars[offset - 1].close
                        ),
                        side=side,
                        atr=atr,
                        bars=bars[offset:],
                        variant=Variant(
                            "PLACEBO_TIME_SHIFT_V2",
                            "IMMEDIATE",
                            variant.stop_atr,
                            variant.take_atr,
                            variant.trail_after_r,
                            variant.trail_atr,
                        ),
                        entry_context=entry_context,
                        roundtrip_cost_price=economics[
                            "roundtrip_cost_price"
                        ],
                        tick_size=economics["tick_size"],
                        stop_slippage_ticks=float(
                            os.getenv(
                                "SHADOW_STOP_SLIPPAGE_TICKS",
                                "1",
                            )
                        ),
                    )
                    for offset in placebo_offsets
                ]

                placebo_r = (
                    sum(result.net_r for result in placebo_results)
                    / len(placebo_results)
                    if placebo_results
                    else None
                )

                rows.append(
                    {
                        "actual_r": actual_r,
                        "shadow_r": outcome.net_r,
                        "gross_shadow_r": (
                            outcome.net_r + roundtrip_cost_r
                            if outcome.net_r is not None
                            else None
                        ),
                        "roundtrip_cost_r": roundtrip_cost_r,
                        "placebo_r": placebo_r,
                        "placebo_control_code":
                            "TIME_SHIFTED_ENTRY_V2",
                        "placebo_control_valid":
                            bool(placebo_results),
                        "placebo_repetitions":
                            len(placebo_results),
                        "trade_date":
                            trade["entry_ts"].date().isoformat(),
                        "regime":
                            str(trade.get("regime") or "UNKNOWN"),
                        "source_id": int(trade["id"]),
                    }
                )

            completed_rows = [
                row
                for row in rows
                if row["shadow_r"] is not None
                and row["actual_r"] is not None
            ]

            pairs = len(completed_rows)

            gross_expectancy = (
                sum(
                    float(row["gross_shadow_r"])
                    for row in completed_rows
                )
                / pairs
                if pairs
                else None
            )

            roundtrip_cost = (
                sum(
                    float(row["roundtrip_cost_r"])
                    for row in completed_rows
                )
                / pairs
                if pairs
                else None
            )

            net_expectancy = (
                sum(
                    float(row["shadow_r"])
                    for row in completed_rows
                )
                / pairs
                if pairs
                else None
            )

            statistical = candidate_statistical_gate(
                completed_rows,
                samples=int(
                    os.getenv(
                        "ENTRY_EXIT_STAT_BOOTSTRAP_SAMPLES",
                        "1000",
                    )
                ),
                seed=731 + grid_index,
            )

            negative_control = negative_control_check(
                completed_rows
            )

            paired_gain = statistical.get(
                "paired_expectancy_gain_r"
            )

            probability_positive = statistical.get(
                "probability_positive"
            )

            placebo_delta = negative_control.get(
                "delta_expectancy_r"
            )

            placebo_delta_lower_bound = negative_control.get(
                "delta_lower_bound_r"
            )

            if pairs < 10:
                state = "INSUFFICIENT_SAMPLE"
            elif (
                gross_expectancy is not None
                and gross_expectancy > 0
                and net_expectancy is not None
                and net_expectancy > 0
                and paired_gain is not None
                and paired_gain > 0
                and placebo_delta_lower_bound is not None
                and placebo_delta_lower_bound > 0
            ):
                state = "TARGET_EDGE"
            elif (
                gross_expectancy is not None
                and gross_expectancy > 0
                and paired_gain is not None
                and paired_gain > 0
            ):
                state = "GROSS_EDGE_BASELINE_SUPERIOR"
            elif (
                paired_gain is not None
                and paired_gain > 0
            ):
                state = "BASELINE_SUPERIOR_GROSS_NEGATIVE"
            else:
                state = "BASELINE_INFERIOR"

            results.append(
                {
                    "code": code,
                    "stop_atr": stop_atr,
                    "take_atr": take_atr,
                    "pairs": pairs,
                    "gross_expectancy": gross_expectancy,
                    "roundtrip_cost": roundtrip_cost,
                    "net_expectancy": net_expectancy,
                    "paired_gain": paired_gain,
                    "probability_positive":
                        probability_positive,
                    "placebo_delta": placebo_delta,
                    "placebo_delta_lower_bound":
                        placebo_delta_lower_bound,
                    "statistical_verdict":
                        statistical.get("verdict"),
                    "state": state,
                }
            )

        results.sort(
            key=lambda row: (
                0 if row["state"] == "TARGET_EDGE" else
                1 if row["state"] ==
                "GROSS_EDGE_BASELINE_SUPERIOR" else
                2 if row["state"] ==
                "BASELINE_SUPERIOR_GROSS_NEGATIVE" else
                3 if row["state"] ==
                "BASELINE_INFERIOR" else
                4,
                -float(row["gross_expectancy"] or -999),
                -float(row["paired_gain"] or -999),
            )
        )

        for rank, row in enumerate(results, start=1):
            print(
                "GRID_RESULT "
                f"rank={rank} "
                f"code={row['code']} "
                f"stop_atr={row['stop_atr']} "
                f"take_atr={row['take_atr']} "
                f"pairs={row['pairs']} "
                f"gross_expectancy="
                f"{row['gross_expectancy']} "
                f"roundtrip_cost="
                f"{row['roundtrip_cost']} "
                f"net_expectancy="
                f"{row['net_expectancy']} "
                f"paired_gain={row['paired_gain']} "
                f"probability_positive="
                f"{row['probability_positive']} "
                f"placebo_delta="
                f"{row['placebo_delta']} "
                f"placebo_delta_lower_bound="
                f"{row['placebo_delta_lower_bound']} "
                f"statistical_verdict="
                f"{row['statistical_verdict']} "
                f"state={row['state']}"
            )

        gross_positive_and_baseline_superior = sum(
            1
            for row in results
            if row["gross_expectancy"] is not None
            and row["gross_expectancy"] > 0
            and row["paired_gain"] is not None
            and row["paired_gain"] > 0
        )

        target_edge_candidates = sum(
            1
            for row in results
            if row["state"] == "TARGET_EDGE"
        )

        completed = sum(
            1 for bundle in bundles
            if bundle[4]
        )

        print("=== PLZL BASELINE SUPERIOR FRONTIER EXTENSION V1 ===")
        print(f"source_bundles={len(bundles)}")
        print(f"completed_horizon_bundles={completed}")
        print("strategy=MEAN_REVERSION_EQUITY")
        print("symbol_group=PLZL")
        print("side=SHORT")
        print("grid_rows=15")

        print("search_executed=1")
        print(
            "gross_positive_and_baseline_superior="
            f"{gross_positive_and_baseline_superior}"
        )
        print(
            "target_edge_candidates="
            f"{target_edge_candidates}"
        )
        print("db_writes_performed=0")
        print("production_pipeline_changed=0")
        print("production_variant_family_changed=0")
        print("thresholds_changed=0")
        print("net_first_logic_changed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        print(
            "VERDICT="
            "PLZL_BASELINE_SUPERIOR_FRONTIER_EXTENSION_V1_READY"
        )
        return 0

    finally:
        conn.rollback()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
