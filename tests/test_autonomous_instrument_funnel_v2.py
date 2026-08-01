from pathlib import Path


def test_funnel_is_provider_discovered_and_auditable() -> None:
    source=Path("src/scripts/run_autonomous_instrument_scout_v1.py").read_text()
    migration=Path("sql/analytics/146_autonomous_instrument_funnel_v2.sql").read_text()
    for stage in ("DISCOVERED","DATA_SPEC","LIQUIDITY","INFORMATION","CATEGORY_QUOTA","COARSE_SEARCH"):
        assert stage in source
        assert stage in migration
    assert "instrument_reference" in source
    assert "market_instrument_v1" in source
    assert "moex_top_universe" in source
    assert "avg_spread_bps" in source
    assert "median_volume" in source
    assert "capacity_rub" in source
    assert "max_abs_correlation" in source
    assert 'max_abs_correlation"]<=float(policy["max_abs_correlation"]' in source
    assert "regime_novelty_score" in source
    assert "reserve_slots" in migration
    assert '"coarse_search_share":0.10' in migration


def test_control_panel_renders_instrument_funnel() -> None:
    renderer=Path("src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py").read_text()
    resolver=Path("src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py").read_text()
    assert "def _instrument_funnel" in renderer
    assert "research.scout.funnel.title" in renderer
    assert "scout_specification_pass" in renderer
    assert "specification_pass,liquidity_pass,information_ranked,coarse_queued" in resolver
    assert '("volatility",s.scout_information_ranked)' in renderer


def test_v3_scout_selects_tradable_volatility_and_caps_top_ten() -> None:
    source=Path("src/scripts/run_autonomous_instrument_scout_v1.py").read_text()
    migration=Path("sql/analytics/253_tradable_volatility_scout_v3.sql").read_text()
    for feature in ("atr_pct","atr_percentile","rv20","rv60","volatility_acceleration",
                    "volume_zscore","directional_efficiency","volatility_persistence",
                    "zero_volume_share","spread_atr_ratio","tradable_volatility_score"):
        assert feature in source
        assert feature in migration
    assert '"max_selected":10' in migration
    assert 'len(selected)>=int(policy["max_selected"])' in source
    assert '"promotion_ceiling":"SHADOW"' in source
    assert "VOLATILITY" in source and "VOLATILITY" in migration
