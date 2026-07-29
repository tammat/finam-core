import importlib.util
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"src/scripts/run_v5_futures_rollover_v1.py"
spec=importlib.util.spec_from_file_location("v5_rollover",SCRIPT)
module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module)


def test_rollover_requires_liquidity_and_window() -> None:
    assert module.choose_rollover(days=20,current_volume=100,current_trades=20,next_volume=50,next_trades=20)==(False,"KEEP_CURRENT_LIQUIDITY")
    assert module.choose_rollover(days=5,current_volume=100,current_trades=20,next_volume=90,next_trades=20)==(True,"ROLLOVER_WINDOW_LIQUID")
    assert module.choose_rollover(days=2,current_volume=100,current_trades=20,next_volume=1,next_trades=0)==(False,"NEXT_LIQUIDITY_NOT_READY")


def test_rollover_is_flat_only_scope_preserving_and_audited() -> None:
    source=SCRIPT.read_text()
    assert "paper_research_position_projection_v1" in source
    assert 'reason="OPEN_POSITION"' in source
    assert "resolve_paper_portfolio_scope_v1" in source
    assert "V5_SCOPE_CHANGED" in source
    assert "SAVEPOINT v5_rollover_switch" in source
    assert "ROLLBACK TO SAVEPOINT v5_rollover_switch" in source
    assert "v5_futures_rollover_decision_v1" in source
    assert "execution_changed=0 orders_changed=0 fills_changed=0 real_allowed=0" in source


def test_rollover_scheduler_is_apply_mode_and_pipeline_reloads_br() -> None:
    scheduler=(ROOT/"src/scripts/run_db_job_scheduler_v1.py").read_text()
    pipeline=(ROOT/"src/finam_core/pipelines/paper_pipeline.py").read_text()
    assert '"V5_FUTURES_FLAT_LIQUIDITY_ROLLOVER_V1"' in scheduler
    assert '"V5_FUTURES_FLAT_LIQUIDITY_ROLLOVER_V1": ["--apply"]' in scheduler
    assert "PIPE_BR_RUNTIME_CONTRACT_SWITCH" in pipeline
    migration=(ROOT/"sql/analytics/220_v5_futures_rollover_v1.sql").read_text()
    assert "market_data_watch_universe" in migration
    assert "V5 rollover candidate prewarm" in migration
    assert "SELECT symbol,asset_group,'M1'" in migration
    assert "ON CONFLICT(symbol)" in migration
