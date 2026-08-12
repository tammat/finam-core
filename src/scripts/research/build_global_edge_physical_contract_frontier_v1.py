from __future__ import annotations

import os
from collections import defaultdict
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.entry_exit_optimizer import (
    candidate_statistical_gate,
    negative_control_check,
)

from scripts.analytics.build_entry_exit_optimizer_v1 import (
    symbol_group as resolve_symbol_group,
)


ZERO = Decimal("0")
MIN_TARGET_PAIRS = 10


def dec(value) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def gap(value: Decimal | None) -> Decimal:
    if value is None:
        return Decimal("999999")
    return max(ZERO, -value)


def state_for(
    *,
    net: Decimal | None,
    paired_gain: Decimal | None,
    placebo_lb: Decimal | None,
    pairs: int,
) -> str:
    if pairs < MIN_TARGET_PAIRS:
        return "INSUFFICIENT_SAMPLE"

    if paired_gain is None:
        return "PAIRED_EVIDENCE_MISSING"

    if (
        net is not None
        and net > 0
        and paired_gain > 0
        and placebo_lb is not None
        and placebo_lb > 0
    ):
        return "TARGET_CANDIDATE"

    if net is not None and net > 0 and paired_gain > 0:
        return "PLACEBO_INFERIOR"

    if net is not None and net > 0 and paired_gain <= 0:
        return "NET_POSITIVE_BASELINE_INFERIOR"

    if net is not None and net <= 0 and paired_gain > 0:
        return "BASELINE_SUPERIOR_NET_NEGATIVE"

    return "NET_NEGATIVE_BASELINE_INFERIOR"


def main() -> int:
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.set_session(readonly=True, autocommit=False)

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Берём только текущих active challengers.
            cur.execute(
                """
                SELECT DISTINCT
                    w.strategy_code,
                    w.symbol_group,
                    w.side_code,
                    w.candidate_code
                FROM analytics.entry_exit_promotion_workflow_v1 w
                WHERE w.evidence #>>
                    '{promotion_workflow,selected_for_shadow_funnel}'
                    = 'true'
                """
            )

            active = {
                (
                    row["strategy_code"],
                    row["symbol_group"],
                    row["side_code"],
                    row["candidate_code"],
                )
                for row in cur.fetchall()
            }

            cur.execute(
                """
                SELECT
                    p.strategy_code,
                    p.symbol_code,
                    p.side_code,
                    p.candidate_code,
                    p.source_signal_id,
                    p.shadow_net_r,
                    p.actual_net_r,
                    p.placebo_net_r,
                    p.is_oos,
                    p.label_start_ts
                FROM analytics.entry_exit_signal_shadow_pair_v2 p
                WHERE p.shadow_net_r IS NOT NULL
                   OR p.actual_net_r IS NOT NULL
                   OR p.placebo_net_r IS NOT NULL
                ORDER BY
                    p.strategy_code,
                    p.symbol_code,
                    p.side_code,
                    p.candidate_code,
                    p.label_start_ts,
                    p.source_signal_id
                """
            )

            grouped: dict[tuple, list[dict]] = defaultdict(list)

            for row in cur.fetchall():
                canonical_group = resolve_symbol_group(
                    row["strategy_code"],
                    row["symbol_code"],
                )

                active_key = (
                    row["strategy_code"],
                    canonical_group,
                    row["side_code"],
                    row["candidate_code"],
                )

                if active_key not in active:
                    continue

                key = (
                    row["strategy_code"],
                    canonical_group,
                    row["symbol_code"],
                    row["side_code"],
                    row["candidate_code"],
                )

                grouped[key].append(row)

        results = []

        for (
            strategy,
            symbol_group,
            physical_symbol,
            side,
            candidate,
        ), source_rows in grouped.items():

            rows = []

            for source in source_rows:
                ts = source["label_start_ts"]

                rows.append(
                    {
                        "shadow_r": (
                            float(source["shadow_net_r"])
                            if source["shadow_net_r"] is not None
                            else None
                        ),
                        "actual_r": (
                            float(source["actual_net_r"])
                            if source["actual_net_r"] is not None
                            else None
                        ),
                        "placebo_r": (
                            float(source["placebo_net_r"])
                            if source["placebo_net_r"] is not None
                            else None
                        ),
                        "placebo_control_code": "TIME_SHIFTED_ENTRY_V2",
                        "placebo_control_valid":
                            source["placebo_net_r"] is not None,
                        "placebo_repetitions": (
                            1 if source["placebo_net_r"] is not None else 0
                        ),
                        "trade_date": (
                            ts.date().isoformat()
                            if ts is not None
                            else "UNKNOWN"
                        ),
                        "regime": "PHYSICAL_CONTRACT",
                        "source_id": int(source["source_signal_id"]),
                    }
                )

            paired = [
                row
                for row in rows
                if row["shadow_r"] is not None
                and row["actual_r"] is not None
            ]

            pairs = len(paired)

            net = (
                Decimal(
                    str(
                        sum(row["shadow_r"] for row in paired)
                        / pairs
                    )
                )
                if pairs
                else None
            )

            actual = (
                Decimal(
                    str(
                        sum(row["actual_r"] for row in paired)
                        / pairs
                    )
                )
                if pairs
                else None
            )

            paired_gain = (
                net - actual
                if net is not None and actual is not None
                else None
            )

            statistical = candidate_statistical_gate(
                paired,
                samples=int(
                    os.getenv(
                        "ENTRY_EXIT_STAT_BOOTSTRAP_SAMPLES",
                        "1000",
                    )
                ),
                seed=731,
            )

            negative = negative_control_check(paired)

            placebo_lb = dec(
                negative.get("delta_lower_bound_r")
            )

            placebo_delta = dec(
                negative.get("delta_expectancy_r")
            )

            oos_pairs = sum(
                1
                for source in source_rows
                if source["is_oos"] is True
                and source["shadow_net_r"] is not None
                and source["actual_net_r"] is not None
            )

            state = state_for(
                net=net,
                paired_gain=paired_gain,
                placebo_lb=placebo_lb,
                pairs=pairs,
            )

            sample_penalty = (
                max(
                    ZERO,
                    Decimal("60") - Decimal(pairs),
                )
                / Decimal("60")
            )

            frontier_gap = (
                gap(net)
                + gap(paired_gain)
                + gap(placebo_lb)
            )

            priority_gap = frontier_gap + sample_penalty

            results.append(
                {
                    "strategy": strategy,
                    "symbol_group": symbol_group,
                    "physical_symbol": physical_symbol,
                    "side": side,
                    "candidate": candidate,
                    "pairs": pairs,
                    "oos_pairs": oos_pairs,
                    "net": net,
                    "actual": actual,
                    "paired_gain": paired_gain,
                    "placebo_delta": placebo_delta,
                    "placebo_lb": placebo_lb,
                    "probability_positive":
                        statistical.get("probability_positive"),
                    "statistical_verdict":
                        statistical.get("verdict"),
                    "state": state,
                    "frontier_gap": frontier_gap,
                    "sample_penalty": sample_penalty,
                    "priority_gap": priority_gap,
                }
            )

        state_order = {
            "TARGET_CANDIDATE": 0,
            "PLACEBO_INFERIOR": 1,
            "NET_POSITIVE_BASELINE_INFERIOR": 2,
            "BASELINE_SUPERIOR_NET_NEGATIVE": 3,
            "INSUFFICIENT_SAMPLE": 4,
            "PAIRED_EVIDENCE_MISSING": 5,
            "NET_NEGATIVE_BASELINE_INFERIOR": 6,
        }

        results.sort(
            key=lambda row: (
                state_order[row["state"]],
                row["priority_gap"],
                -row["pairs"],
                row["physical_symbol"],
            )
        )

        for rank, row in enumerate(results, start=1):
            print(
                "PHYSICAL_FRONTIER_ROW "
                f"rank={rank} "
                f"state={row['state']} "
                f"strategy={row['strategy']} "
                f"symbol_group={row['symbol_group']} "
                f"physical_symbol={row['physical_symbol']} "
                f"side={row['side']} "
                f"candidate={row['candidate']} "
                f"pairs={row['pairs']} "
                f"oos_pairs={row['oos_pairs']} "
                f"net_expectancy={row['net']} "
                f"actual_expectancy={row['actual']} "
                f"paired_gain={row['paired_gain']} "
                f"placebo_delta={row['placebo_delta']} "
                f"placebo_delta_lower_bound={row['placebo_lb']} "
                f"probability_positive="
                f"{row['probability_positive']} "
                f"statistical_verdict="
                f"{row['statistical_verdict']} "
                f"frontier_gap={row['frontier_gap']} "
                f"sample_penalty={row['sample_penalty']} "
                f"priority_gap={row['priority_gap']}"
            )

        target_candidates = sum(
            row["state"] == "TARGET_CANDIDATE"
            for row in results
        )

        brq6_present = any(
            row["physical_symbol"] == "BRQ6@RTSX"
            for row in results
        )

        bru6_present = any(
            row["physical_symbol"] == "BRU6@RTSX"
            for row in results
        )

        print(f"physical_cohorts={len(results)}")
        print(f"target_candidates={target_candidates}")
        print(f"brq6_present={int(brq6_present)}")
        print(f"bru6_present={int(bru6_present)}")

        print("physical_contract_identity_used=1")
        print("contract_mixing_allowed=0")
        print("physical_contract_segmentation_materialized=1")

        print("db_writes_performed=0")
        print("production_pipeline_changed=0")
        print("thresholds_changed=0")
        print("net_first_logic_changed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        print(
            "VERDICT="
            "GLOBAL_EDGE_PHYSICAL_CONTRACT_FRONTIER_V1_READY"
        )

        return 0

    finally:
        conn.rollback()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
