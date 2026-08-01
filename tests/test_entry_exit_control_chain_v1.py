from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_chain_is_locked_and_ordered():
    source = (ROOT / "src/scripts/run_entry_exit_control_chain_v1.py").read_text(encoding="utf-8")
    assert "pg_try_advisory_lock" in source
    assert source.index("build_entry_exit_optimizer_v1.py") < source.index("maintain_entry_exit_oos_admissions_v1.py")
    assert source.index("maintain_entry_exit_oos_admissions_v1.py") < source.index("run_v5_purged_oos_worker_v1.py")
    assert source.index("run_v5_purged_oos_worker_v1.py") < source.index("run_adaptive_regime_pilot_v1.py")


def test_optimizer_preselects_one_variant_before_simulation():
    source = (ROOT / "src/scripts/analytics/build_entry_exit_optimizer_v1.py").read_text(encoding="utf-8")
    selection = source.index("frozen_pool_row")
    simulation = source.index("for variant in variants:", selection)
    assert selection < simulation
    assert "variants = (by_variant_code[frozen_code],)" in source


def test_pilot_snapshots_and_restores_baseline():
    source = (ROOT / "src/scripts/run_adaptive_regime_pilot_v1.py").read_text(encoding="utf-8")
    assert "ensure_paper_baseline" in source
    assert "CURRENT_PAPER_BASELINE" in source
    assert "AUTO_PILOT_ROLLBACK_V1" in source
    assert "entry_exit_promotion_workflow_v1 w" in source
    assert "w.workflow_stage<>'REJECTED'" in source
