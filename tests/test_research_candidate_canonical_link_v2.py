from pathlib import Path


def test_lineage_uses_discovery_batch_and_observation_uuid() -> None:
    source=Path("src/scripts/build_profit_funnel_transition_lineage_v2.py").read_text()
    assert "observations_scanned" in source
    assert "c.discovery_batch_id=l.discovery_batch_id" in source
    assert "o.observation_uuid=c.observation_uuid" in source
    assert 'reason_code="OBSERVATION_UUID_FULL_MATCH"' in source


def test_oos_forward_gap_uses_explicit_handoff_not_symbol_matching() -> None:
    source=Path("src/scripts/build_profit_funnel_transition_lineage_v2.py").read_text()
    assert "h.candidate_uuid=c.candidate_uuid" in source
    assert "f.incubator_candidate_id=h.forward_candidate_id" in source
    assert 'reason_code="HANDOFF_PENDING_FORWARD_ADMISSION"' in source
    assert "symbol=c.symbol" not in source
