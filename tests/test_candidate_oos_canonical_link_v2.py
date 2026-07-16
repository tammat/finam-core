from pathlib import Path


def test_oos_builder_reads_registered_candidates_without_hardcoded_batch() -> None:
    source=Path("src/scripts/build_momentum_edge_oos_rank_v1.py").read_text()
    assert 'os.getenv("RESEARCH_BATCH_ID")' in source
    assert "JOIN analytics.edge_candidate_v1 c ON c.observation_uuid=o.observation_uuid" in source
    assert '"20260712_MOMENTUM_THRESHOLD_RECALC_V2"' not in source
    assert "observation[\"research_batch_id\"]" in source


def test_oos_result_updates_the_same_candidate_lifecycle() -> None:
    source=Path("src/scripts/build_momentum_edge_oos_rank_v1.py").read_text()
    assert "UPDATE analytics.edge_candidate_v1" in source
    assert "WHERE observation_uuid=%s" in source
    assert "validation_stage='OOS_COMPLETE'" in source
