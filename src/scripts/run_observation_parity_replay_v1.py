from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

from finam_core.research.observation_parity_v1 import compare_observation

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> int:
    totals = {"MATCH": 0, "MISMATCH": 0, "NOT_PROVEN": 0}
    with psycopg2.connect(DB) as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext('observation_parity_replay_v1'))")
        cur.execute("""SELECT r.admission_id,r.timeframe AS frozen_timeframe,p.*,
               s.payload AS signal_payload,s.status AS signal_status,
               s.qty AS runtime_qty,s.entry_price AS runtime_signal_price,s.timeframe AS runtime_timeframe,
               pe.entry_mode AS pending_mode,pe.status AS pending_status,
               pe.decision_reason AS runtime_decision,pe.resolved_entry_price,
               ct.entry_price AS paper_entry_price,ct.exit_price AS paper_exit_price,
               ct.qty AS paper_qty,ct.commission,ct.net_pnl,ct.payload AS trade_payload
          FROM analytics.v5_post_fix_branch_registry_v1 r
          JOIN analytics.entry_exit_signal_shadow_pair_v2 p
            ON p.symbol_code=r.observation_symbol AND p.strategy_code=r.strategy_code
           AND p.side_code=r.side_code AND p.candidate_code=r.candidate_code
          JOIN public.signals s ON s.id=p.source_signal_id
          LEFT JOIN LATERAL (SELECT * FROM analytics.entry_exit_pending_entry_v1 pe
             WHERE pe.signal_id=p.signal_id AND pe.candidate_code=p.candidate_code
             ORDER BY pe.created_at DESC LIMIT 1) pe ON true
          LEFT JOIN LATERAL (SELECT * FROM public.closed_trades ct
             WHERE ct.signal_id=p.signal_id AND ct.trade_source='paper'
             ORDER BY coalesce(ct.exit_ts,ct.closed_at,ct.created_at) DESC LIMIT 1) ct ON true
          WHERE p.label_start_ts>=r.frozen_at ORDER BY p.source_signal_id""")
        for row in map(dict, cur.fetchall()):
            signal_payload = row.get("signal_payload") or {}
            runtime_features = signal_payload.get("features") or {}
            trade_payload = row.get("trade_payload") or {}
            research = {
                "features": row.get("entry_context") or {},
                "decision": row.get("entry_decision"), "entry_mode": row.get("entry_mode"),
                "side": row.get("side_code"), "timeframe": row.get("frozen_timeframe"),
                "entry_price": None, "quantity": None, "exit_price": None,
                "costs": None,
                "net_r": row.get("shadow_net_r"),
            }
            runtime = {
                "features": runtime_features,
                "decision": row.get("pending_mode") or
                    runtime_features.get("adaptive_entry_effective_mode") or
                    ("IMMEDIATE" if row.get("signal_status") == "FILLED" else None),
                "entry_mode": row.get("pending_mode") or runtime_features.get("adaptive_entry_effective_mode"),
                "side": row.get("side_code"), "timeframe": row.get("runtime_timeframe"),
                "entry_price": row.get("paper_entry_price") or row.get("resolved_entry_price"),
                "quantity": row.get("paper_qty") or row.get("runtime_qty"),
                "exit_price": row.get("paper_exit_price"),
                "costs": trade_payload.get("cost_r"),
                "net_r": trade_payload.get("net_pnl_r") or
                    (trade_payload.get("context") or {}).get("net_pnl_r"),
            }
            verdict, reasons = compare_observation(research, runtime)
            cur.execute("""INSERT INTO analytics.observation_parity_v1(
                admission_id,source_signal_id,signal_id,candidate_code,research_observation,
                runtime_observation,verdict_code,reason_codes)
              VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
              ON CONFLICT(admission_id,source_signal_id,candidate_code) DO UPDATE SET
                research_observation=excluded.research_observation,
                runtime_observation=excluded.runtime_observation,
                verdict_code=excluded.verdict_code,reason_codes=excluded.reason_codes,
                checked_at=clock_timestamp()""", (
                row["admission_id"],row["source_signal_id"],row["signal_id"],row["candidate_code"],
                psycopg2.extras.Json(research),psycopg2.extras.Json(runtime),verdict,
                psycopg2.extras.Json(reasons)))
            totals[verdict] += 1
    print(" ".join(f"{key.lower()}={value}" for key,value in totals.items()))
    print("VERDICT=OBSERVATION_PARITY_REPLAY_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
