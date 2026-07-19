from pathlib import Path


def test_economic_hypotheses_keep_meta_entry_v2_and_explicit_regimes():
    source=Path("src/scripts/sync_economic_hypothesis_algorithms_v1.py").read_text()
    assert '"entry_policy_code":"META_ENTRY_V2"' in source
    assert source.count('"allowed_regimes"') >= 6
    assert '"exit_trail_atr"' in source
    assert '"exit_volatility_risk_multiplier"' in source


def test_regime_discovery_rejects_incomplete_contract_with_auditable_code():
    source=Path("src/scripts/build_edge_regime_hypothesis_discovery_v2.py").read_text()
    assert 'REGIME_POLICY_ALLOWED_REGIMES_MISSING' in source
    assert "apply_meta_entry_policy_v2" in source
