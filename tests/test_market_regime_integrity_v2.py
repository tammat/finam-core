from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_context_is_causal_fresh_and_v5_only():
    source = (ROOT / "src" / "scripts" / "build_market_regime_context_v2.py").read_text()
    assert "bar_ts+interval '1 minute'<=%s" in source
    assert 'Decimal(str(ages["mx_age"])) > 600' in source
    assert 'rvi_fresh = Decimal(str(ages["rvi_age"])) <= 1800' in source
    assert "payload->>'portfolio_scope','') LIKE 'FRESH_V5%%'" in source
    assert "payload->>'execution_type','')='paper'" in source
    assert "upper(s.status) IN('ACCEPTED','RISK_ACCEPTED','FILLED')" in source
    policy = (ROOT / "src" / "scripts" / "build_market_regime_context_v1.py").read_text()
    assert 'return "SKIP", Decimal("0"), "RVI_STALE"' in policy


def test_shadow_outcomes_use_later_closes_and_costs():
    source = (ROOT / "src" / "scripts" / "build_market_regime_context_v2.py").read_text()
    assert "ts>%s" in source
    assert "STOP_CLOSE_CONFIRMED" in source
    assert "TARGET_CLOSE_CONFIRMED" in source
    assert "execution_cost=%s,net_pnl=%s" in source
    assert 'bar["high"]' not in source
    assert 'bar["low"]' not in source


def test_scheduler_order_and_cleanup_are_explicit():
    migration = (ROOT / "sql" / "analytics" / "238_market_regime_integrity_v2.sql").read_text()
    assert "SET priority=60" in migration
    assert "executor_code='MARKET_REGIME_CONTEXT_V2',priority=61" in migration
    assert "SET priority=62" in migration
    assert "market_regime_cleanup_audit_v2" in migration
    assert "DELETE FROM analytics.market_regime_shadow_variant_v1" in migration
