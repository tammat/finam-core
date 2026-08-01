from __future__ import annotations

import os
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "V5_PURGED_OOS_WORKER_V2"
MINIMUM_OBSERVATIONS = int(os.getenv("V5_OOS_MINIMUM_OBSERVATIONS", "20"))
MINIMUM_PROFIT_FACTOR = Decimal(os.getenv("V5_OOS_MINIMUM_PROFIT_FACTOR", "1.15"))


def _context(trade: dict) -> dict[str, str]:
    payload = trade.get("payload") or {}
    context = payload.get("context") or {}
    return {
        "strategy": str(trade.get("strategy") or "UNASSIGNED"),
        "side": str(trade.get("side") or "UNKNOWN").upper(),
        "session": str(context.get("entry_session_msk") or "UNKNOWN"),
        "regime": str(context.get("entry_regime") or trade.get("entry_regime") or "UNKNOWN"),
        # The cohort key must be known at entry. actual_exit_reason is an outcome,
        # retained only in the audit payload and never used for admission/matching.
        "exit": str(context.get("planned_exit_rule") or context.get("exit_rule") or "UNKNOWN"),
        "candidate": str(context.get("candidate_code") or ""),
    }


def _matches(request: dict, trade: dict) -> bool:
    actual = _context(trade)
    expected = {
        "strategy": str(request.get("paper_strategy_code") or "UNASSIGNED"),
        "side": str(request.get("side_code") or "UNKNOWN").upper(),
        "session": str(request.get("session_code") or "UNKNOWN"),
        "regime": str(request.get("regime_code") or "UNKNOWN"),
        "exit": str(request.get("holding_code") or "UNKNOWN"),
        "candidate": str((request.get("frozen_profile") or {}).get("candidate_code") or ""),
    }
    return all(expected[key] in {"", "None", "*"} or actual[key] == expected[key] for key in expected)


def classify_observation(run: dict, request: dict, trade: dict, *, reused: bool = False) -> tuple[str, str]:
    if trade["exit_ts"] <= run["purge_before_ts"]:
        return "EXCLUDED_PRE_BOUNDARY", "TRADE_NOT_AFTER_FROZEN_V5_BOUNDARY"
    if trade["entry_ts"] < run["confirmation_after_ts"]:
        return "EXCLUDED_EMBARGO_OR_OVERLAP", "ENTRY_BEFORE_CONFIRMATION_AFTER_TS"
    if not _matches(request, trade):
        return "EXCLUDED_CONTEXT", "TRADE_CONTEXT_DOES_NOT_MATCH_ADMISSION"
    return "INCLUDED", "FUTURE_ONLY_PREREGISTERED_CONTEXT_MATCH"


def _ensure_run(cur, admission: dict) -> dict:
    isolation = admission["oos_request"]["temporal_isolation"]
    run_id = uuid.uuid5(uuid.UUID("8c84345a-0388-47f4-9a09-81dc86f43ff2"), str(admission["admission_id"]))
    cur.execute("""INSERT INTO analytics.v5_oos_run_v1(
        run_id,admission_id,hypothesis_id,purge_before_ts,confirmation_after_ts,
        embargo_seconds,minimum_observations,status_code)
      VALUES(%s,%s,%s,%s,%s,%s,%s,'COLLECTING') ON CONFLICT(admission_id) DO NOTHING""",
      (str(run_id),admission["admission_id"],admission["hypothesis_id"],isolation["purge_before_ts"],
       isolation["confirmation_after_ts"],int(isolation["embargo_seconds"]),MINIMUM_OBSERVATIONS))
    cur.execute("SELECT * FROM analytics.v5_oos_run_v1 WHERE admission_id=%s", (admission["admission_id"],))
    return dict(cur.fetchone())


def _audit_trade(cur, run: dict, admission: dict, trade: dict) -> None:
    request = admission["oos_request"]
    decision,reason=classify_observation(run,request,trade)
    cur.execute("""INSERT INTO analytics.v5_oos_observation_audit_v1(
        run_id,admission_id,source_trade_id,signal_id,entry_ts,exit_ts,decision_code,
        reason_code,net_pnl,event_cluster_id,source_payload)
      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,
        analytics.v5_oos_event_cluster_id_v2(%s,%s,%s),%s)
      ON CONFLICT(run_id,source_trade_id) DO NOTHING""",
      (run["run_id"],admission["admission_id"],trade["id"],trade["signal_id"],trade["entry_ts"],
       trade["exit_ts"],decision,reason,trade["net_pnl"],trade.get("symbol") or request.get("symbol"),trade["entry_ts"],
       trade["exit_ts"],psycopg2.extras.Json({"context":_context(trade)})))


def _finish(cur, run: dict, admission: dict) -> None:
    cur.execute("""WITH independent_events AS (
        SELECT event_cluster_id,avg(net_pnl) net_pnl
        FROM analytics.v5_oos_observation_audit_v1
        WHERE run_id=%s AND decision_code='INCLUDED' GROUP BY event_cluster_id
      ) SELECT (SELECT count(*) FROM analytics.v5_oos_observation_audit_v1
                WHERE run_id=%s AND decision_code='INCLUDED') raw_included,
        count(*) included,excluded_counts.excluded,
        coalesce(sum(net_pnl),0) net_pnl,avg(net_pnl) expectancy,
        sum(net_pnl) FILTER(WHERE net_pnl>0) gross_profit,
        abs(sum(net_pnl) FILTER(WHERE net_pnl<0)) gross_loss
      FROM independent_events CROSS JOIN LATERAL (
        SELECT count(*) FILTER(WHERE decision_code<>'INCLUDED') excluded
        FROM analytics.v5_oos_observation_audit_v1 WHERE run_id=%s) excluded_counts
      GROUP BY excluded_counts.excluded""", (run["run_id"],run["run_id"],run["run_id"]))
    metric = dict(cur.fetchone())
    included = int(metric["included"] or 0)
    gross_loss = Decimal(str(metric["gross_loss"] or 0))
    pf = Decimal(str(metric["gross_profit"] or 0)) / gross_loss if gross_loss > 0 else None
    expectancy = Decimal(str(metric["expectancy"] or 0))
    if included < int(run["minimum_observations"]):
        status, reason = "COLLECTING", "WAITING_FUTURE_OBSERVATIONS"
        admission_status = "RUNNING"
    elif expectancy > 0 and pf is not None and pf >= MINIMUM_PROFIT_FACTOR:
        status, reason, admission_status = "OOS_PASS", "V5_PURGED_OOS_EDGE_CONFIRMED", "OOS_PASS"
    else:
        status, reason, admission_status = "OOS_FAIL", "V5_PURGED_OOS_GATE_FAILED", "OOS_FAIL"
    cur.execute("""UPDATE analytics.v5_oos_run_v1 SET status_code=%s,observations_included=%s,
        observations_excluded=%s,raw_observations_included=%s,effective_observations=%s,
        net_pnl=%s,expectancy=%s,profit_factor=%s,reason_code=%s,
        updated_at=clock_timestamp() WHERE run_id=%s""",
      (status,included,int(metric["excluded"] or 0),int(metric["raw_included"] or 0),included,
       metric["net_pnl"],metric["expectancy"],pf,reason,run["run_id"]))
    cur.execute("""UPDATE analytics.trade_outcome_oos_admission_v1 SET status_code=%s,reason_code=%s,
        updated_at=clock_timestamp() WHERE admission_id=%s""", (admission_status,reason,admission["admission_id"]))


def main() -> int:
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT pg_try_advisory_xact_lock(184002) locked")
            if not cur.fetchone()["locked"]:
                print("VERDICT=V5_PURGED_OOS_WORKER_ALREADY_RUNNING")
                return 0
            cur.execute("""SELECT * FROM analytics.trade_outcome_oos_admission_v1
                WHERE status_code IN ('QUEUED','RUNNING')
                  AND oos_request->'temporal_isolation'->>'policy'='PURGED_EMBARGO_V5_V1'
                ORDER BY admission_id""")
            admissions = [dict(row) for row in cur.fetchall()]
            for admission in admissions:
                run = _ensure_run(cur, admission)
                request = admission["oos_request"]
                if request.get("observation_source") == "ENTRY_EXIT_SHADOW_V2":
                    cur.execute("""SELECT source_signal_id AS id,signal_id,symbol_code AS symbol,
                        side_code AS side,strategy_code AS strategy,
                        coalesce(entry_context->>'regime','UNKNOWN') AS entry_regime,
                        label_start_ts AS entry_ts,label_end_ts AS exit_ts,
                        shadow_net_r AS net_pnl,
                        jsonb_build_object('context',entry_context || jsonb_build_object(
                          'candidate_code',candidate_code,'planned_exit_rule','*')) AS payload
                      FROM analytics.entry_exit_signal_shadow_pair_v2
                      WHERE symbol_code=%s AND strategy_code=%s AND side_code=%s
                        AND candidate_code=%s AND shadow_net_r IS NOT NULL
                        AND label_end_ts >= %s - (%s * interval '1 second')
                      ORDER BY label_end_ts,source_signal_id""",
                      (request["symbol"],request["paper_strategy_code"],request["side_code"],
                       request["frozen_profile"]["candidate_code"],run["purge_before_ts"],
                       run["embargo_seconds"]))
                else:
                    cur.execute("""SELECT id,signal_id,symbol,side,strategy,entry_regime,entry_ts,exit_ts,
                        net_pnl,payload FROM public.closed_trades
                      WHERE symbol=%s
                        AND coalesce(trade_source,'')='paper'
                        AND coalesce(portfolio_scope,'') LIKE 'FRESH_V5%%'
                        AND coalesce(payload->'context'->>'cohort','')=portfolio_scope
                        AND exit_ts >= %s - (%s * interval '1 second')
                      ORDER BY exit_ts,id""",
                      (request["symbol"],run["purge_before_ts"],run["embargo_seconds"]))
                for trade in cur.fetchall():
                    _audit_trade(cur,run,admission,dict(trade))
                _finish(cur,run,admission)
    print(f"admissions_processed={len(admissions)}")
    print("promotion_allowed=0 live_allowed=0")
    print(f"VERDICT={SOURCE_VERSION}_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
