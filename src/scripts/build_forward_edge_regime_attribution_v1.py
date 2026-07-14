from __future__ import annotations

import os
from pathlib import Path

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "sql" / "analytics" / "047_forward_edge_regime_attribution_v1.sql"
SOURCE_VERSION = "FORWARD_EDGE_REGIME_ATTRIBUTION_V1"
MAX_SNAPSHOT_AGE = "15 minutes"


def main() -> int:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(MIGRATION.read_text(encoding="utf-8"))
            cur.execute("""
                SELECT cohort_id
                FROM analytics.forward_edge_incubator_v1
                ORDER BY created_at DESC
                LIMIT 1
            """)
            latest = cur.fetchone()
            if not latest:
                print("cohort=none")
                print("VERDICT=FORWARD_EDGE_REGIME_ATTRIBUTION_V1_NO_COHORT")
                return 0
            cohort_id = latest["cohort_id"]

            cur.execute("""
                SELECT DISTINCT policy_code
                FROM analytics.forward_edge_shadow_exit_variant_v1
                WHERE cohort_id=%s
                ORDER BY policy_code
            """, (cohort_id,))
            policies = [row["policy_code"] for row in cur.fetchall()]
            if not policies:
                print(f"cohort_id={cohort_id}")
                print("policies=0")
                print("VERDICT=FORWARD_EDGE_REGIME_ATTRIBUTION_V1_NO_VARIANTS")
                return 0

            rows_written = 0
            for policy_code in policies:
                cur.execute("""
                    WITH attributed AS (
                        SELECT
                            o.*,
                            COALESCE(r.regime, 'UNKNOWN') AS attributed_regime,
                            r.confidence AS regime_confidence,
                            EXTRACT(EPOCH FROM (o.entry_ts-r.ts)) AS snapshot_age_seconds
                        FROM analytics.forward_edge_observation_v1 o
                        LEFT JOIN LATERAL (
                            SELECT s.ts,s.regime,s.confidence
                            FROM public.analytics_regime_snapshots_v2 s
                            WHERE s.symbol=o.symbol
                              AND s.timeframe=o.timeframe
                              AND s.ts<=o.entry_ts
                              AND s.ts>=o.entry_ts-(%s::interval)
                            ORDER BY s.ts DESC
                            LIMIT 1
                        ) r ON true
                        WHERE o.cohort_id=%s
                    ), metrics AS (
                        SELECT
                            a.attributed_regime AS regime_code,
                            count(*)::integer AS observations_total,
                            count(*) FILTER (WHERE a.observation_status='CLOSED')::integer AS baseline_closed,
                            COALESCE(sum(a.net_pnl) FILTER (WHERE a.observation_status='CLOSED'),0) AS baseline_net_pnl,
                            avg((a.net_pnl>0)::integer) FILTER (WHERE a.observation_status='CLOSED') AS baseline_win_rate,
                            count(v.*) FILTER (WHERE v.variant_status='CLOSED')::integer AS variant_closed,
                            COALESCE(sum(v.net_pnl) FILTER (WHERE v.variant_status='CLOSED'),0) AS variant_net_pnl,
                            avg((v.net_pnl>0)::integer) FILTER (WHERE v.variant_status='CLOSED') AS variant_win_rate,
                            avg(a.regime_confidence) AS avg_regime_confidence,
                            max(a.snapshot_age_seconds) AS max_snapshot_age_seconds
                        FROM attributed a
                        LEFT JOIN analytics.forward_edge_shadow_exit_variant_v1 v
                          ON v.observation_id=a.observation_id AND v.policy_code=%s
                        GROUP BY a.attributed_regime
                    )
                    INSERT INTO analytics.forward_edge_regime_attribution_v1 (
                        cohort_id,policy_code,regime_code,observations_total,
                        baseline_closed,baseline_net_pnl,baseline_win_rate,
                        variant_closed,variant_net_pnl,variant_win_rate,net_pnl_delta,
                        avg_regime_confidence,max_snapshot_age_seconds,attribution_status,source_version
                    )
                    SELECT
                        %s,%s,regime_code,observations_total,
                        baseline_closed,baseline_net_pnl,baseline_win_rate,
                        variant_closed,variant_net_pnl,variant_win_rate,
                        variant_net_pnl-baseline_net_pnl,
                        avg_regime_confidence,max_snapshot_age_seconds,
                        CASE WHEN regime_code='UNKNOWN' THEN 'UNKNOWN' ELSE 'ATTRIBUTED' END,
                        %s
                    FROM metrics
                    ON CONFLICT (cohort_id,policy_code,regime_code) DO UPDATE SET
                        observations_total=excluded.observations_total,
                        baseline_closed=excluded.baseline_closed,
                        baseline_net_pnl=excluded.baseline_net_pnl,
                        baseline_win_rate=excluded.baseline_win_rate,
                        variant_closed=excluded.variant_closed,
                        variant_net_pnl=excluded.variant_net_pnl,
                        variant_win_rate=excluded.variant_win_rate,
                        net_pnl_delta=excluded.net_pnl_delta,
                        avg_regime_confidence=excluded.avg_regime_confidence,
                        max_snapshot_age_seconds=excluded.max_snapshot_age_seconds,
                        attribution_status=excluded.attribution_status,
                        source_version=excluded.source_version,
                        updated_at=now()
                    RETURNING regime_code
                """, (
                    MAX_SNAPSHOT_AGE, cohort_id, policy_code,
                    cohort_id, policy_code, SOURCE_VERSION,
                ))
                rows_written += len(cur.fetchall())

            cur.execute("""
                SELECT policy_code,regime_code,observations_total,baseline_closed,
                       round(baseline_net_pnl,4) AS baseline_net_pnl,
                       variant_closed,round(variant_net_pnl,4) AS variant_net_pnl,
                       round(net_pnl_delta,4) AS net_pnl_delta,
                       round(avg_regime_confidence,4) AS avg_confidence,
                       attribution_status
                FROM analytics.forward_edge_regime_attribution_v1
                WHERE cohort_id=%s AND policy_code=ANY(%s)
                ORDER BY policy_code,regime_code
            """, (cohort_id, policies))
            report = cur.fetchall()

    print(f"cohort_id={cohort_id}")
    print(f"policies={len(policies)}")
    print(f"rows_written={rows_written}")
    for row in report:
        print(
            "regime={regime_code} observations={observations_total} "
            "baseline_closed={baseline_closed} baseline_net={baseline_net_pnl} "
            "variant_closed={variant_closed} variant_net={variant_net_pnl} "
            "delta={net_pnl_delta} confidence={avg_confidence} status={attribution_status}".format(**row)
        )
    print("runtime_changed=0")
    print("execution_changed=0")
    print("broker_orders=0")
    print("VERDICT=FORWARD_EDGE_REGIME_ATTRIBUTION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
