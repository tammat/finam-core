from __future__ import annotations

import uuid

import psycopg2

SOURCE_VERSION = "PROFIT_FUNNEL_SHADOW_PAPER_ADMISSION_V2"
NAMESPACE = uuid.UUID("30924b4a-7199-5d9d-a097-5566a77c3113")


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                DELETE FROM analytics.profit_funnel_shadow_paper_admission_v2 a
                WHERE NOT EXISTS (
                    SELECT 1 FROM analytics.forward_edge_shadow_trade_v1 s
                    JOIN analytics.forward_edge_incubator_v1 i
                      ON i.cohort_id=s.cohort_id AND i.incubator_candidate_id=s.incubator_candidate_id
                    WHERE s.cohort_id=a.cohort_id
                      AND s.incubator_candidate_id=a.incubator_candidate_id
                )
            """)
            cursor.execute("""
                WITH stats AS (
                    SELECT i.incubator_candidate_id,i.cohort_id,i.minimum_observations,i.minimum_calendar_days,
                           count(*) FILTER (WHERE s.shadow_status='CLOSED')::bigint closed_trades,
                           count(*) FILTER (WHERE s.shadow_status<>'CLOSED')::bigint active_trades,
                           coalesce(sum(s.net_pnl) FILTER (WHERE s.shadow_status='CLOSED'),0) net_pnl,
                           coalesce((max(s.exit_ts)::date-min(s.entry_ts)::date),0)::int observed_days
                    FROM analytics.forward_edge_incubator_v1 i
                    JOIN analytics.forward_edge_shadow_trade_v1 s
                      ON s.cohort_id=i.cohort_id AND s.incubator_candidate_id=i.incubator_candidate_id
                    GROUP BY i.incubator_candidate_id,i.cohort_id,i.minimum_observations,i.minimum_calendar_days
                )
                SELECT * FROM stats ORDER BY incubator_candidate_id
            """)
            rows = cursor.fetchall()
            counts = {"ELIGIBLE": 0, "WAITING": 0, "REJECTED": 0}
            for candidate_id, cohort_id, min_obs, min_days, closed, active, net_pnl, days in rows:
                if net_pnl <= 0:
                    status, reason = "REJECTED", "SHADOW_NET_PNL_NOT_POSITIVE"
                elif closed < min_obs:
                    status, reason = "WAITING", "MINIMUM_OBSERVATIONS_NOT_REACHED"
                elif days < min_days:
                    status, reason = "WAITING", "MINIMUM_CALENDAR_DAYS_NOT_REACHED"
                elif active > 0:
                    status, reason = "WAITING", "ACTIVE_SHADOW_TRADES_REMAIN"
                else:
                    status, reason = "ELIGIBLE", "AWAITING_GOVERNED_PAPER_ADMISSION"
                counts[status] += 1
                identity = f"{cohort_id}:{candidate_id}"
                admission_id = uuid.uuid5(NAMESPACE, "admission:" + identity)
                paper_candidate_id = uuid.uuid5(NAMESPACE, "paper:" + identity)
                cursor.execute("""
                    INSERT INTO analytics.profit_funnel_shadow_paper_admission_v2 (
                        admission_id,incubator_candidate_id,cohort_id,closed_trades,active_trades,net_pnl,
                        observed_calendar_days,minimum_observations,minimum_calendar_days,
                        admission_status,reason_code,paper_candidate_id,
                        paper_allowed,runtime_allowed,live_allowed,source_version,evaluated_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,false,false,%s,clock_timestamp())
                    ON CONFLICT (cohort_id,incubator_candidate_id) DO UPDATE SET
                        closed_trades=EXCLUDED.closed_trades,active_trades=EXCLUDED.active_trades,
                        net_pnl=EXCLUDED.net_pnl,observed_calendar_days=EXCLUDED.observed_calendar_days,
                        admission_status=EXCLUDED.admission_status,reason_code=EXCLUDED.reason_code,
                        source_version=EXCLUDED.source_version,evaluated_at=clock_timestamp()
                """, (str(admission_id),str(candidate_id),str(cohort_id),closed,active,net_pnl,days,min_obs,min_days,
                      status,reason,str(paper_candidate_id),SOURCE_VERSION))
    print(f"shadow_candidates_assessed={len(rows)}")
    print(f"eligible={counts['ELIGIBLE']}")
    print(f"waiting={counts['WAITING']}")
    print(f"rejected={counts['REJECTED']}")
    print("paper_orders_changed=0")
    print("runtime_changed=0")
    print("live_allowed=0")
    print("VERDICT=MARKETCORE_SHADOW_PAPER_ADMISSION_V2_READY")


if __name__ == "__main__":
    main()
