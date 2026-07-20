from pathlib import Path


def test_profit_aware_compute_policy_preserves_gates_and_blocks_rsi() -> None:
    migration = Path("sql/analytics/144_edge_algorithm_compute_policy_v1.sql").read_text()
    assert "DONCHIAN_VOL_BREAKOUT',1,'FOCUS'" in migration
    assert "EMA_TREND',2,'SECONDARY'" in migration
    assert "MOMENTUM',3,'LIMITED'" in migration
    assert "RSI',90,'ANOMALY_REVIEW',0,0,true" in migration
    assert "edge_algorithm_anomaly_review_v1" in migration


def test_adaptive_generator_obeys_compute_budget() -> None:
    source = Path("src/scripts/generate_adaptive_edge_search_scenarios_v1.py").read_text()
    assert "compute_priority_rank" in source
    assert "compute_budget" in source
    assert "promotion_blocked" in source
    assert 'algorithm_code == "DONCHIAN_VOL_BREAKOUT"' in source
    assert 'algorithm_code == "EMA_TREND"' in source
    assert '"exit_policy_code": "DYNAMIC_EXIT_V1"' in source
    assert '"entry_policy_code": "META_ENTRY_V2"' in source


def test_checkpoint_schema_is_fold_granular_and_two_stage() -> None:
    migration = Path("sql/analytics/145_checkpointed_walkforward_queue_v1.sql").read_text()
    assert "walkforward_algorithm_task_v4" in migration
    assert "walkforward_variant_task_v4" in migration
    assert "walkforward_fold_checkpoint_v4" in migration
    assert "PRIMARY KEY(variant_task_id,fold_no)" in migration
    assert "top_share numeric NOT NULL DEFAULT .10" in migration
    assert "cpu_limit integer NOT NULL DEFAULT 2" in migration
    assert "walkforward_feature_cache_v4" in migration
