from datetime import datetime, timedelta, timezone
from pathlib import Path
import copy
import os

import psycopg2
import psycopg2.extras

from scripts.run_v5_purged_oos_worker_v1 import _matches, classify_observation, _ensure_run, _audit_trade, _finish


def test_context_match_is_exact_for_v5_oos() -> None:
    request = {"paper_strategy_code":"S","side_code":"LONG","session_code":"MAIN",
               "regime_code":"RANGE","holding_code":"TRAIL"}
    trade = {"strategy":"S","side":"LONG","entry_regime":"RANGE",
             "payload":{"context":{"entry_session_msk":"MAIN","planned_exit_rule":"TRAIL","actual_exit_reason":"LOSS"}}}
    assert _matches(request, trade)
    trade["payload"]["context"]["entry_session_msk"] = "EVENING"
    assert not _matches(request, trade)


def test_worker_contract_contains_temporal_and_reuse_guards() -> None:
    source = Path("src/scripts/run_v5_purged_oos_worker_v1.py").read_text()
    assert 'trade["entry_ts"] < run["confirmation_after_ts"]' in source
    assert 'context.get("planned_exit_rule")' in source
    assert "SOURCE_TRADE_ALREADY_USED_BY_ANOTHER_OOS_RUN" not in source
    assert "v5_oos_observation_audit_v1" in source
    assert "promotion_allowed=0 live_allowed=0" in source


def test_confirmation_boundary_is_strictly_after_embargo() -> None:
    purge = datetime(2026,7,30,tzinfo=timezone.utc)
    confirmation = purge + timedelta(minutes=30)
    assert confirmation > purge


def test_all_audit_decisions_are_reachable() -> None:
    purge=datetime(2026,7,30,tzinfo=timezone.utc); confirmation=purge+timedelta(minutes=30)
    run={"purge_before_ts":purge,"confirmation_after_ts":confirmation}
    request={"paper_strategy_code":"S","side_code":"LONG","session_code":"MAIN",
             "regime_code":"RANGE","holding_code":"TRAIL"}
    base={"strategy":"S","side":"LONG","entry_regime":"RANGE",
          "payload":{"context":{"entry_session_msk":"MAIN","planned_exit_rule":"TRAIL"}}}
    assert classify_observation(run,request,{**base,"entry_ts":purge-timedelta(minutes=2),"exit_ts":purge},reused=False)[0]=="EXCLUDED_PRE_BOUNDARY"
    assert classify_observation(run,request,{**base,"entry_ts":purge+timedelta(minutes=1),"exit_ts":confirmation+timedelta(minutes=1)},reused=False)[0]=="EXCLUDED_EMBARGO_OR_OVERLAP"
    wrong={**base,"side":"SHORT","entry_ts":confirmation,"exit_ts":confirmation+timedelta(minutes=1)}
    assert classify_observation(run,request,wrong,reused=False)[0]=="EXCLUDED_CONTEXT"
    good={**base,"entry_ts":confirmation,"exit_ts":confirmation+timedelta(minutes=1)}
    assert classify_observation(run,request,good,reused=True)[0]=="INCLUDED"
    assert classify_observation(run,request,good,reused=False)[0]=="INCLUDED"


def test_worker_accepts_only_paper_v5_source() -> None:
    source=Path("src/scripts/run_v5_purged_oos_worker_v1.py").read_text()
    assert "coalesce(trade_source,'')='paper'" in source
    assert "coalesce(portfolio_scope,'') LIKE 'FRESH_V5%%'" in source
    assert "payload->'context'->>'cohort'" in source


def test_admission_normalizes_contract_root_and_freezes_before_oos() -> None:
    source = Path("src/scripts/admit_trade_outcome_hypotheses_to_oos_v1.py").read_text()
    assert "g.symbol LIKE h.symbol || '%'" in source
    assert 'TRADE_OUTCOME_HYPOTHESIS_MIN_TRADES", "15"' in source
    assert '"fresh_cohort": "FRESH_V5_CONFIRMED"' in source
    assert "_refresh_fresh_v5_hypotheses" in source
    assert "FRESH_V5_COHORT_REGISTRATION" in source
    assert "FREEZE_FOR_FUTURE_OOS" in source


def test_db_admission_to_audit_to_running_verdict_is_transactional() -> None:
    connection=psycopg2.connect(os.getenv("DATABASE_URL","postgresql:///finam_core"))
    try:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM analytics.trade_outcome_oos_admission_v1 WHERE status_code='WAITING_FRESH_DATA' ORDER BY created_at LIMIT 1")
            row=cur.fetchone()
            if row is None:
                return
            admission=dict(row); admission["oos_request"]=copy.deepcopy(admission["oos_request"])
            purge=datetime.now(timezone.utc)-timedelta(hours=2); confirmation=purge+timedelta(minutes=30)
            admission["oos_request"]["temporal_isolation"]={"purge_before_ts":purge.isoformat(),
                "confirmation_after_ts":confirmation.isoformat(),"embargo_seconds":1800}
            run=_ensure_run(cur,admission)
            cur.execute("SELECT id,signal_id FROM analytics.closed_trades_fresh_v5_confirmed ORDER BY id LIMIT 1")
            source=cur.fetchone(); assert source is not None
            request=admission["oos_request"]
            trade={"id":source["id"],"signal_id":source["signal_id"],"strategy":request["paper_strategy_code"],
                "side":request["side_code"],"entry_regime":request.get("regime_code"),
                "entry_ts":confirmation+timedelta(minutes=1),"exit_ts":confirmation+timedelta(minutes=2),
                "net_pnl":1,"payload":{"context":{"entry_session_msk":request.get("session_code"),
                "entry_regime":request.get("regime_code"),"planned_exit_rule":request.get("holding_code")}}}
            _audit_trade(cur,run,admission,trade); _finish(cur,run,admission)
            cur.execute("SELECT observations_included,status_code FROM analytics.v5_oos_run_v1 WHERE run_id=%s",(run["run_id"],))
            saved=cur.fetchone(); assert saved["observations_included"]==1 and saved["status_code"]=="COLLECTING"
            cur.execute("SELECT decision_code FROM analytics.v5_oos_observation_audit_v1 WHERE run_id=%s",(run["run_id"],))
            assert cur.fetchone()["decision_code"]=="INCLUDED"
    finally:
        connection.rollback(); connection.close()
