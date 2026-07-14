from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "sql" / "analytics" / "049_forward_edge_loss_decomposition_v1.sql"
SOURCE_VERSION = "FORWARD_EDGE_LOSS_DECOMPOSITION_V1"
RECONCILIATION_TOLERANCE = Decimal("0.0001")


def dec(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def dominant_loss_driver(row: dict[str, Any]) -> str:
    drivers = {
        "RAW_EDGE": max(-dec(row["reference_gross_pnl"]), Decimal("0")),
        "ENTRY_TIMING": max(dec(row["entry_timing_cost"]), Decimal("0")),
        "COMMISSION": dec(row["commission_cost"]),
        "SPREAD": dec(row["spread_cost"]),
        "SLIPPAGE": dec(row["slippage_cost"]),
        "EXIT_POLICY": max(-dec(row["exit_policy_effect"]), Decimal("0")),
    }
    driver, loss = max(drivers.items(), key=lambda item: item[1])
    return driver if loss > 0 else "NONE"


def reconciliation_error(row: dict[str, Any]) -> Decimal:
    expected = (
        dec(row["reference_gross_pnl"])
        - dec(row["entry_timing_cost"])
        - dec(row["commission_cost"])
        - dec(row["spread_cost"])
        - dec(row["slippage_cost"])
        + dec(row["exit_policy_effect"])
    )
    return dec(row["variant_net_pnl"]) - expected


def main() -> int:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(MIGRATION.read_text(encoding="utf-8"))
            cur.execute("SELECT cohort_id FROM analytics.forward_edge_incubator_v1 ORDER BY created_at DESC LIMIT 1")
            latest = cur.fetchone()
            if not latest:
                print("VERDICT=FORWARD_EDGE_LOSS_DECOMPOSITION_V1_NO_COHORT")
                return 0
            cohort_id = latest["cohort_id"]
            cur.execute("""
                WITH detailed AS (
                    SELECT
                        i.incubator_candidate_id,i.strategy_family,v.policy_code,
                        COALESCE(reg.regime,'UNKNOWN') AS regime_code,
                        o.observation_id,o.gross_pnl AS baseline_gross_pnl,o.net_pnl AS baseline_net_pnl,
                        v.gross_pnl AS variant_gross_pnl,v.net_pnl AS variant_net_pnl,
                        COALESCE(v.commission,0) AS commission_cost,
                        COALESCE(v.spread_cost,0) AS spread_cost,
                        COALESCE(v.slippage,0) AS slippage_cost,
                        ref.close AS signal_reference_close,
                        CASE WHEN ref.close IS NULL THEN NULL ELSE
                            (o.exit_price-ref.close) * CASE WHEN o.side='LONG' THEN 1 ELSE -1 END
                        END AS reference_gross_pnl,
                        CASE WHEN ref.close IS NULL THEN NULL ELSE
                            (o.entry_price-ref.close) * CASE WHEN o.side='LONG' THEN 1 ELSE -1 END
                        END AS entry_timing_cost
                    FROM analytics.forward_edge_incubator_v1 i
                    JOIN analytics.forward_edge_observation_v1 o USING (cohort_id,incubator_candidate_id)
                    JOIN analytics.forward_edge_shadow_exit_variant_v1 v ON v.observation_id=o.observation_id
                    LEFT JOIN LATERAL (
                        SELECT r.regime FROM analytics_regime_snapshots_v2 r
                        WHERE r.symbol=o.symbol AND r.timeframe=o.timeframe
                          AND r.ts<=o.entry_ts AND r.ts>=o.entry_ts-interval '15 minutes'
                        ORDER BY r.ts DESC LIMIT 1
                    ) reg ON true
                    LEFT JOIN LATERAL (
                        SELECT b.close FROM public.market_bars b
                        WHERE b.symbol=o.symbol AND b.timeframe=o.timeframe
                          AND b.ts<=o.signal_ts AND b.ts>=o.signal_ts-interval '5 minutes'
                        ORDER BY b.ts DESC LIMIT 1
                    ) ref ON true
                    WHERE i.cohort_id=%s AND o.observation_status='CLOSED' AND v.variant_status='CLOSED'
                )
                SELECT
                    incubator_candidate_id,strategy_family,policy_code,regime_code,
                    count(*)::integer AS closed_observations,
                    count(signal_reference_close)::integer AS entry_reference_observations,
                    count(signal_reference_close)::numeric/count(*) AS entry_reference_coverage,
                    COALESCE(sum(reference_gross_pnl),0) AS reference_gross_pnl,
                    COALESCE(sum(entry_timing_cost),0) AS entry_timing_cost,
                    COALESCE(sum(baseline_gross_pnl),0) AS realized_baseline_gross_pnl,
                    COALESCE(sum(commission_cost),0) AS commission_cost,
                    COALESCE(sum(spread_cost),0) AS spread_cost,
                    COALESCE(sum(slippage_cost),0) AS slippage_cost,
                    COALESCE(sum(baseline_net_pnl),0) AS baseline_net_pnl,
                    COALESCE(sum(variant_gross_pnl-baseline_gross_pnl),0) AS exit_policy_effect,
                    COALESCE(sum(variant_net_pnl),0) AS variant_net_pnl
                FROM detailed
                GROUP BY incubator_candidate_id,strategy_family,policy_code,regime_code
                ORDER BY incubator_candidate_id,policy_code,regime_code
            """, (cohort_id,))
            rows = [dict(row) for row in cur.fetchall()]
            status_counts = {
                "COMPLETE": 0,
                "PARTIAL_ENTRY_REFERENCE": 0,
                "PARTIAL_COST_MODEL": 0,
                "RECONCILIATION_ERROR": 0,
            }
            driver_counts: dict[str, int] = {}
            for row in rows:
                error = reconciliation_error(row)
                if abs(error) > RECONCILIATION_TOLERANCE:
                    quality = "RECONCILIATION_ERROR"
                elif dec(row["entry_reference_coverage"]) < Decimal("1"):
                    quality = "PARTIAL_ENTRY_REFERENCE"
                elif dec(row["spread_cost"]) == 0 and dec(row["slippage_cost"]) == 0:
                    quality = "PARTIAL_COST_MODEL"
                else:
                    quality = "COMPLETE"
                driver = dominant_loss_driver(row)
                status_counts[quality] += 1
                driver_counts[driver] = driver_counts.get(driver, 0) + 1
                cur.execute("""
                    INSERT INTO analytics.forward_edge_loss_decomposition_v1 (
                        cohort_id,incubator_candidate_id,policy_code,strategy_family,regime_code,
                        closed_observations,entry_reference_observations,entry_reference_coverage,
                        reference_gross_pnl,entry_timing_cost,realized_baseline_gross_pnl,
                        commission_cost,spread_cost,slippage_cost,baseline_net_pnl,
                        exit_policy_effect,variant_net_pnl,reconciliation_error,
                        dominant_loss_driver,data_quality_status,source_version
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (cohort_id,incubator_candidate_id,policy_code,regime_code) DO UPDATE SET
                        closed_observations=excluded.closed_observations,
                        entry_reference_observations=excluded.entry_reference_observations,
                        entry_reference_coverage=excluded.entry_reference_coverage,
                        reference_gross_pnl=excluded.reference_gross_pnl,
                        entry_timing_cost=excluded.entry_timing_cost,
                        realized_baseline_gross_pnl=excluded.realized_baseline_gross_pnl,
                        commission_cost=excluded.commission_cost,spread_cost=excluded.spread_cost,
                        slippage_cost=excluded.slippage_cost,baseline_net_pnl=excluded.baseline_net_pnl,
                        exit_policy_effect=excluded.exit_policy_effect,variant_net_pnl=excluded.variant_net_pnl,
                        reconciliation_error=excluded.reconciliation_error,
                        dominant_loss_driver=excluded.dominant_loss_driver,
                        data_quality_status=excluded.data_quality_status,source_version=excluded.source_version,
                        updated_at=now()
                """, (
                    cohort_id,row["incubator_candidate_id"],row["policy_code"],row["strategy_family"],row["regime_code"],
                    row["closed_observations"],row["entry_reference_observations"],row["entry_reference_coverage"],
                    row["reference_gross_pnl"],row["entry_timing_cost"],row["realized_baseline_gross_pnl"],
                    row["commission_cost"],row["spread_cost"],row["slippage_cost"],row["baseline_net_pnl"],
                    row["exit_policy_effect"],row["variant_net_pnl"],error,driver,quality,SOURCE_VERSION,
                ))

    print(f"cohort_id={cohort_id}")
    print(f"decomposition_rows={len(rows)}")
    for status, count in status_counts.items():
        print(f"quality_{status.lower()}={count}")
    for driver, count in sorted(driver_counts.items()):
        print(f"driver_{driver.lower()}={count}")
    print("promotion_allowed=0")
    print("live_allowed=0")
    print("VERDICT=FORWARD_EDGE_LOSS_DECOMPOSITION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
