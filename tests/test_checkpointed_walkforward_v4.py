from pathlib import Path


def test_worker_is_fold_checkpointed_and_early_prunes() -> None:
    source=Path("src/scripts/run_checkpointed_walkforward_v4.py").read_text()
    assert "walkforward_fold_checkpoint_v4" in source
    assert "RECOVERED_AFTER_STOP" in source
    assert "EARLY_INSUFFICIENT_TRADES" in source
    assert "EARLY_NEGATIVE_EXPECTANCY" in source
    assert "COARSE_NOT_TOP_10_PERCENT" in source
    assert "rank_pct<=.10" in source
    assert "cpu_limit={CPU_LIMIT}" in source
    assert "attempts=attempts+1" in source
    assert "variants_complete" in source
    assert "def _select_clean_holdout" in source
    assert "NOT_SELECTED_FOR_CLEAN_HOLDOUT" in source
    assert "generate_series(3,4)" in source
    assert "SELECT variant_task_id,5" in source


def test_autonomous_cycle_uses_checkpointed_worker() -> None:
    source=Path("src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    assert '"WALKFORWARD": "src/scripts/run_checkpointed_walkforward_v4.py"' in source
    assert 'step.endswith("run_checkpointed_walkforward_v4.py")' in source
