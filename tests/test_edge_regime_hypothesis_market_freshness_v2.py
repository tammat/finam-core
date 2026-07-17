from pathlib import Path


def test_regime_discovery_only_uses_current_markets() -> None:
    source = Path("src/scripts/build_edge_regime_hypothesis_discovery_v2.py").read_text()
    universe = Path("src/scripts/edge_research_universe_v1.py").read_text()
    assert 'EDGE_SEARCH_FRESHNESS_MINUTES' in source
    assert "max(b.ts)>=clock_timestamp()-(%s * interval '1 minute')" in universe
    assert "transaction_cost_bps" in source
    assert "promotion_allowed" in source
