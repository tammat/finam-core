from pathlib import Path
import os

import psycopg2
import psycopg2.extras

from scripts.run_v5_purged_oos_worker_v1 import _audit_trade


ROOT = Path(__file__).resolve().parents[1]


def test_audit_has_separate_paper_and_shadow_sources():
    sql = (ROOT / "sql/analytics/262_direct_v5_source_integrity_v1.sql").read_text()
    worker = (ROOT / "src/scripts/run_v5_purged_oos_worker_v1.py").read_text()
    assert "source_signal_id bigint" in sql
    assert "v5_oos_audit_exactly_one_source_check" in sql
    assert "v5_oos_audit_source_signal_fkey" in sql
    assert "v5_oos_included_signal_once_idx" in sql
    assert 'source_kind = "SHADOW_SIGNAL"' in worker
    assert "SOURCE_OBSERVATION_ALREADY_USED_BY_ANOTHER_OOS_RUN" in worker


def test_current_program_lock_blocks_new_cohorts():
    sql = (ROOT / "sql/analytics/262_direct_v5_source_integrity_v1.sql").read_text()
    optimizer = (ROOT / "src/scripts/analytics/build_entry_exit_optimizer_v1.py").read_text()
    assert "CURRENT_V5_FOUR_BRANCHES_ONLY" in sql
    assert "CURRENT_V5_FOUR_BRANCHES_ONLY" in optimizer
    assert "v5_post_fix_branch_registry_v1" in optimizer


def test_direct_v5_reactivates_original_boundaries():
    sql = (ROOT / "sql/analytics/262_direct_v5_source_integrity_v1.sql").read_text()
    assert "DIRECT_V5_POST_FIX_V1" in sql
    assert "SET state_code='V5_COLLECTING'" in sql
    assert "SET status_code='COLLECTING'" in sql


def test_shadow_signal_audit_uses_signal_fk_and_rolls_back():
    connection = psycopg2.connect(os.getenv("DATABASE_URL", "postgresql:///finam_core"))
    try:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""SELECT a.*,v.run_id,v.purge_before_ts,v.confirmation_after_ts
              FROM analytics.v5_post_fix_branch_registry_v1 r
              JOIN analytics.trade_outcome_oos_admission_v1 a ON a.admission_id=r.admission_id
              JOIN analytics.v5_oos_run_v1 v ON v.admission_id=a.admission_id
              WHERE r.branch_code='GLDRUBF_LONG_M5_POST_FIX_V1'""")
            admission = dict(cur.fetchone())
            run = {"run_id": admission["run_id"], "purge_before_ts": admission["purge_before_ts"],
                   "confirmation_after_ts": admission["confirmation_after_ts"]}
            cur.execute("""SELECT source_signal_id,signal_id,symbol_code symbol,side_code side,
              strategy_code strategy,'UNKNOWN' entry_regime,label_start_ts entry_ts,
              label_end_ts exit_ts,shadow_net_r net_pnl,
              jsonb_build_object('context',entry_context || jsonb_build_object(
                'candidate_code',candidate_code,'planned_exit_rule','*')) payload
              FROM analytics.entry_exit_signal_shadow_pair_v2
              WHERE candidate_code='EXPERT_GOLD_CONFIRM_MTF' AND shadow_net_r IS NOT NULL LIMIT 1""")
            trade = dict(cur.fetchone())
            _audit_trade(cur,run,admission,trade)
            cur.execute("""SELECT source_kind,source_trade_id,source_signal_id
              FROM analytics.v5_oos_observation_audit_v1
              WHERE run_id=%s AND source_signal_id=%s""", (run["run_id"],trade["source_signal_id"]))
            saved = cur.fetchone()
            assert saved["source_kind"] == "SHADOW_SIGNAL"
            assert saved["source_trade_id"] is None
            assert saved["source_signal_id"] == trade["source_signal_id"]
    finally:
        connection.rollback()
        connection.close()
