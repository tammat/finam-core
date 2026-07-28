from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_atomic_policy_and_clean_v4_contract():
    sql=(ROOT/'sql/analytics/204_atomic_universe_strategy_policy_v2.sql').read_text()
    assert 'activate_instrument_with_strategy_policy_v2' in sql
    assert 'ACTIVE_UNIVERSE_WITHOUT_STRATEGY_POLICY' in sql
    assert 'MEAN_REVERSION_EQUITY' in sql
    assert 'VOLATILITY_BREAKOUT_EQUITY' in sql
    assert "'UNASSIGNED'" in sql

def test_generic_paper_execute_is_guarded():
    source=(ROOT/'src/finam_core/pipelines/paper_pipeline.py').read_text()
    marker='assignment_allowed, assignment_reason = self._db_atomic_strategy_policy_gate_v2(intent)'
    gate=source.index(marker)
    execute=source.index('raw_fill = self.paper.execute(intent, st)',gate)
    assert gate < execute
    assert 'STRATEGY_POLICY_UNKNOWN_REGIME' in source
    assert source.count('assignment_allowed, assignment_reason = self._db_atomic_strategy_policy_gate_v2(intent)') >= 2

def test_runtime_timeframe_alias_is_normalized_before_policy_lookup():
    source=(ROOT/'src/finam_core/pipelines/paper_pipeline.py').read_text()
    method=source.index('def _db_atomic_strategy_policy_gate_v2')
    normalize=source.index(
        'timeframe = self.candle_regime_engine_v2._normalize_timeframe(timeframe)',
        method,
    )
    lookup=source.index('from analytics.runtime_strategy_policy_v2', method)
    assert method < normalize < lookup

def test_runtime_allocator_uses_atomic_activation_for_every_path():
    source=(ROOT/'src/finam_core/runtime/runtime_universe_allocator.py').read_text()
    assert source.count('activate_instrument_with_strategy_policy_v2') >= 2
    assert 'rejected_missing_atomic_strategy_policy' in source
    assert "range_strategy = \"MEAN_REVERSION_EQUITY\"" in source
    assert "trend_strategy = \"VOLATILITY_BREAKOUT_EQUITY\"" in source
    assert "insert into runtime_active_universe" not in source

def test_db_assignments_preserve_equity_regime_routing():
    source=(ROOT/'src/finam_core/runtime/runtime_universe_allocator.py').read_text()
    contract=source.index('# DB-назначения являются отдельным контрактом')
    equity=source.index('if str(asset_group).upper() == "EQUITY":', contract)
    activate=source.index('select analytics.activate_instrument_with_strategy_policy_v2', equity)
    assert contract < equity < activate
    assert 'range_strategy = "MEAN_REVERSION_EQUITY"' in source[equity:activate]
    assert 'trend_strategy = "VOLATILITY_BREAKOUT_EQUITY"' in source[equity:activate]

def test_atomic_activation_uses_limited_security_definer():
    sql=(ROOT/'sql/analytics/205_atomic_universe_policy_execution_v2.sql').read_text()
    assert 'SECURITY DEFINER' in sql
    assert 'search_path = pg_catalog, public, analytics' in sql
    assert 'REVOKE ALL ON analytics.runtime_strategy_policy_v2 FROM finam' in sql

def test_core_equities_have_atomic_db_assignments():
    sql=(ROOT/'sql/analytics/209_core_equity_strategy_assignment_v1.sql').read_text()
    for symbol in ('SBER@MISX','GAZP@MISX','LKOH@MISX','NVTK@MISX','VTBR@MISX'):
        assert symbol in sql
    assert 'MEAN_REVERSION_EQUITY' in sql
    assert 'VOLATILITY_BREAKOUT_EQUITY' in sql
    assert 'activate_instrument_with_strategy_policy_v2' in sql

def test_runtime_entry_and_promotion_policy_is_db_driven():
    sql=(ROOT/'sql/analytics/211_runtime_entry_and_promotion_policy_v1.sql').read_text()
    assert 'runtime_entry_guard_policy_v1' in sql
    assert 'minimum_paper_trades' in sql
    assert 'minimum_orderbook_coverage' in sql
    assert 'degradation_warning_ratio' in sql
    assert 'degradation_block_ratio' in sql
    assert "('EQUITY', true, true, true" in sql
    assert "('FUTURES', true, true, true" in sql

def test_atomic_gate_is_symmetric_and_fail_closed():
    source=(ROOT/'src/finam_core/pipelines/paper_pipeline.py').read_text()
    method=source.index('def _db_atomic_strategy_policy_gate_v2')
    body=source[method:source.index('def _execute_br_signal_in_paper',method)]
    assert 'STRATEGY_POLICY_UNKNOWN_REGIME' in body
    assert 'STRATEGY_POLICY_UNASSIGNED' in body
    assert 'VOLATILITY_UNCONFIRMED' in body
    assert 'LONG_BLOCKED_CONFIRMED_DOWNTREND' in body
    assert 'SHORT_BLOCKED_CONFIRMED_UPTREND' in body
    assert 'EXPECTED_MOVE_BELOW_COSTS' in body

def test_atomic_gate_consumes_only_fresh_confirmed_candle_volatility():
    source=(ROOT/'src/finam_core/pipelines/paper_pipeline.py').read_text()
    method=source.index('def _db_atomic_strategy_policy_gate_v2')
    body=source[method:source.index('def _execute_br_signal_in_paper',method)]
    assert 'or features.get("volatility")' in body
    assert 'regime_source == "CANDLE_REGIME_V2"' in body
    assert 'not regime_data_ready' in body
    assert 'regime_stale' in body
    assert 'regime_confirmed_bars <= 0' in body

def test_intent_carries_candle_confirmation_contract_to_atomic_gate():
    source=(ROOT/'src/finam_core/pipelines/paper_pipeline.py').read_text()
    assert '"regime_data_ready": bool(getattr(regime, "data_ready", False))' in source
    assert '"regime_stale": bool(getattr(regime, "stale", True))' in source
