from __future__ import annotations

import argparse

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    args = parser.parse_args()

    with psycopg.connect(build_psycopg_url()) as conn, conn.cursor() as cur:
        # Only contexts independently classified FULL may repair attribution.
        cur.execute(
            """
            UPDATE trade_attribution_v2 a
            SET heat_status=r.heat_status,
                risk_multiplier=r.risk_multiplier,
                exit_policy=e.exit_policy,
                attribution_quality=CASE
                    WHEN a.lifecycle_action IN ('SYNC_LIFECYCLE_QTY','REBUILD_LIFECYCLE_STATE')
                        THEN 'RISK_CONTEXT_WEAK'
                    WHEN COALESCE(a.strategy,'')<>''
                     AND COALESCE(a.timeframe,'')<>''
                     AND r.heat_status<>'unknown'
                     AND COALESCE(a.lifecycle_action,'')<>''
                     AND COALESCE(e.exit_policy,'')<>'' THEN 'FULL'
                    ELSE 'PARTIAL'
                END,
                reason=CASE
                    WHEN a.lifecycle_action IN ('SYNC_LIFECYCLE_QTY','REBUILD_LIFECYCLE_STATE')
                        THEN 'lifecycle_state_problem:' || a.lifecycle_action
                    WHEN COALESCE(a.strategy,'')<>''
                     AND COALESCE(a.timeframe,'')<>''
                     AND r.heat_status<>'unknown'
                     AND COALESCE(a.lifecycle_action,'')<>''
                     AND COALESCE(e.exit_policy,'')<>'' THEN 'all_core_context_available'
                    ELSE a.reason
                END
            FROM trade_risk_context r
            JOIN trade_exit_policy_context e USING (closed_trade_id)
            WHERE a.closed_trade_id=r.closed_trade_id
              AND a.symbol=%s
              AND r.context_quality='FULL'
              AND e.context_quality='FULL'
            """,
            (args.symbol,),
        )
        repaired = cur.rowcount
        cur.execute(
            """
            SELECT COUNT(*)
            FROM analytics.trade_context_quarantine_v1
            WHERE symbol=%s AND resolved_at IS NULL
            """,
            (args.symbol,),
        )
        quarantined = int(cur.fetchone()[0])
        conn.commit()

    print(
        f"TRADE_GOVERNANCE_BACKFILL symbol={args.symbol} "
        f"repaired={repaired} quarantined={quarantined}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
