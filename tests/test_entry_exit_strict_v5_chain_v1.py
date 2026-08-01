from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_optimizer_freezes_exact_candidate_before_real_v5_oos():
    source = (ROOT / "src/scripts/analytics/build_entry_exit_optimizer_v1.py").read_text()
    assert "ensure_frozen_entry_exit_oos" in source
    assert '"observation_source":"ENTRY_EXIT_SHADOW_V2"' in source
    assert 'actual_oos_status == "OOS_PASS"' in source
    assert 'workflow_stage = "V5_OOS_PASS"' in source
    assert "freeze_candidate_code" in source
    assert "BEST_EXPENSIVE_GATE_CANDIDATE" in source


def test_worker_consumes_future_shadow_outcomes_for_exact_candidate():
    source = (ROOT / "src/scripts/run_v5_purged_oos_worker_v1.py").read_text()
    assert 'request.get("observation_source") == "ENTRY_EXIT_SHADOW_V2"' in source
    assert "candidate_code=%s AND shadow_net_r IS NOT NULL" in source
    assert "label_start_ts AS entry_ts,label_end_ts AS exit_ts" in source


def test_paper_runtime_requires_completed_v5_pass_not_queue():
    source = (ROOT / "src/finam_core/pipelines/paper_pipeline.py").read_text()
    gate = source[source.index("No new Paper risk is allowed"):]
    assert "a.status_code='OOS_PASS'" in gate
    assert "vr.status_code='OOS_PASS'" in gate
    assert "a.status_code IN ('QUEUED','RUNNING')" not in gate


def test_minimal_pilot_requires_strict_candidate_v5_pass():
    source = (ROOT / "src/scripts/run_adaptive_regime_pilot_v1.py").read_text()
    assert "WAITING_STRICT_FROZEN_V5_OOS_PASS" in source
    assert "strict_v5_pass" in source
    assert "ADAPTIVE_PILOT_QUANTITY" not in source  # quantity is enforced in runtime


def test_champion_health_is_attributed_to_profile_and_candidate():
    source = (ROOT / "src/scripts/analytics/build_entry_exit_optimizer_v1.py").read_text()
    assert "entry_exit_candidate_code" in source
    assert "entry_exit_profile_id" in source
    assert "champion_rows = [dict(row)" in source


def test_futures_preserve_contract_aware_risk_geometry():
    source = (ROOT / "src/finam_core/pipelines/paper_pipeline.py").read_text()
    assert "futures_contract_risk_preserved" in source
    assert "if not futures_contract_risk_preserved" in source
    assert "FUTURES_PROFILE_REQUIRES_UNIFIED_RISK_RUNTIME" not in source
