from pathlib import Path
import importlib.util
import sys


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "src/finam_core/risk/asset_specific_volatility_gate_v1.py"
MIGRATION = ROOT / "sql/analytics/217_v5_multi_asset_scopes_and_branches_v1.sql"
ROLLOVER = ROOT / "sql/analytics/218_v5_asset_contract_rollover_readiness_v1.sql"
ROTATION = ROOT / "src/scripts/rotate_v5_asset_branch_timeframes_v1.py"
PIPELINE = ROOT / "src/finam_core/pipelines/paper_pipeline.py"
RESOLVER = ROOT / "src/marketcore/presentation/workspace_v2/resolver/control_compact_v3_resolver.py"
RENDERER = ROOT / "src/marketcore/presentation/workspace_v2/renderer/control_compact_v3_domain_renderer.py"

spec = importlib.util.spec_from_file_location("asset_vol_gate", GATE)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_asset_gate_uses_own_history_percentile() -> None:
    gate = module.AssetSpecificVolatilityGateV1()
    ok = gate.decide(symbol="USDRUBF@RTSX",atr_pct=.001,atr_percentile=.5,
                     data_ready=True,stale=False)
    low = gate.decide(symbol="GDU6@RTSX",atr_pct=.001,atr_percentile=.1,
                      data_ready=True,stale=False)
    assert ok.applies and ok.allowed and ok.asset_code == "USD"
    assert low.applies and not low.allowed
    assert low.reason_code == "GOLD_VOLATILITY_BELOW_OWN_HISTORY"


def test_asset_gate_fails_closed_without_fresh_history() -> None:
    decision = module.AssetSpecificVolatilityGateV1().decide(
        symbol="CNYRUBF@RTSX",atr_pct=.001,atr_percentile=.5,data_ready=False,stale=True
    )
    assert decision.applies and not decision.allowed
    assert decision.reason_code == "CNY_VOLATILITY_HISTORY_NOT_READY"


def test_three_assets_have_isolated_scopes_and_twelve_branches() -> None:
    sql = MIGRATION.read_text()
    for scope in ("FRESH_V5_USD_PERPETUAL","FRESH_V5_GOLD_FUTURES","FRESH_V5_CNY_PERPETUAL"):
        assert scope in sql
    assert "CROSS JOIN (VALUES('M1'),('M5'))" in sql
    assert "CROSS JOIN (VALUES('LONG'),('SHORT'))" in sql
    for guard in ("cost_guard_required","session_guard_required","direction_guard_required",
                  "candle_exit_required","trailing_dry_run_required","funding_cost_required"):
        assert guard in sql


def test_asset_scopes_do_not_replace_br_ng_fallback_scope() -> None:
    sql = MIGRATION.read_text()
    assert "explicit_scope" in sql and "fallback_scope" in sql
    assert "FRESH_V5_CONFIRMED_FUTURES" in sql


def test_pipeline_no_longer_applies_br_gate_to_asset_specific_futures() -> None:
    text = PIPELINE.read_text()
    assert "AssetSpecificVolatilityGateV1" in text
    assert "regime_atr_percentile" in text


def test_rollover_readiness_keeps_oos_blocked_without_dated_lineage() -> None:
    sql = ROLLOVER.read_text()
    assert "USDRUBF@RTSX" in sql and "CNYRUBF@RTSX" in sql
    assert "GDU6@RTSX" in sql and "GDZ6@RTSX" in sql
    assert "research_entry_allowed" in sql
    assert "oos_allowed" in sql
    assert "SwapRate funding is mandatory" in sql
    pipeline = PIPELINE.read_text()
    assert "_v5_asset_contract_allows_signal" in pipeline
    assert "CONTRACT_ROLLOVER" in pipeline


def test_asset_positions_use_active_m1_or_m5_candle_exit_clock() -> None:
    pipeline = PIPELINE.read_text()
    assert "def _exit_timeframe_for_symbol" in pipeline
    assert 'timeframe in {"M1", "M5"}' in pipeline
    assert "expected_timeframe = self._exit_timeframe_for_symbol(symbol)" in pipeline
    assert "timeframe = self._exit_timeframe_for_symbol(symbol)" in pipeline
    exit_engine = (ROOT / "src/finam_core/strategy/exit_engine.py").read_text()
    assert 'if side == "BUY"' in exit_engine
    assert 'if side == "SELL"' in exit_engine


def test_timeframe_rotation_never_switches_an_open_asset_position() -> None:
    source = ROTATION.read_text()
    assert "paper_research_position_projection_v1" in source
    assert "if bool(cursor.fetchone()[\"has_position\"]):" in source
    assert "skipped_open += 1" in source
    assert "LEAST_OBSERVED_FLAT_BRANCH" in source


def test_timeframe_rotation_is_allowlisted_research_only() -> None:
    scheduler = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    migration = (ROOT / "sql/analytics/219_v5_asset_branch_rotation_v1.sql").read_text()
    assert '"V5_ASSET_BRANCH_ROTATION_V1": "src/scripts/rotate_v5_asset_branch_timeframes_v1.py"' in scheduler
    assert "V5_ASSET_BRANCH_ROTATION_V1" in migration
    source = ROTATION.read_text()
    assert "execution_changed=0 orders_changed=0 fills_changed=0 real_allowed=0" in source


def test_compact_ui_shows_asset_branches_without_new_controls() -> None:
    resolver = RESOLVER.read_text()
    renderer = RENDERER.read_text()
    for scope in ("FRESH_V5_USD_PERPETUAL", "FRESH_V5_GOLD_FUTURES",
                  "FRESH_V5_CNY_PERPETUAL"):
        assert scope in resolver
    assert '"asset_branches": asset_branches' in resolver
    assert '"cny_spot_controls": cny_spot_controls' in resolver
    section = renderer[renderer.index("def _multi_asset_section"):renderer.index("def _ru_status")]
    assert "Валюты и золото" in section
    assert "LONG" in section and "SHORT" in section
    assert "funding required" in section and "rollover required" in section
    assert "DATA/COST NOT READY" in section
    assert "_command(" not in section
