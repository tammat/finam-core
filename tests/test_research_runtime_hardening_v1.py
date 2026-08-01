from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_research_supervisor_defers_under_load():
    source = (ROOT / "src/finam_core/research/research_runtime_supervisor.py").read_text()
    assert "RESEARCH_RUNTIME_MAX_LOAD_1M" in source
    assert "RESEARCH_RUNTIME_SUPERVISOR_DEFERRED" in source
    assert 'status="DEFERRED"' in source


def test_active_universe_requires_policy_and_live_contract():
    source = (ROOT / "src/scripts/sync_runtime_active_universe_from_strategy_selection.py").read_text()
    assert "runtime_strategy_policy_v2" in source
    assert "futures_contract_universe" in source
    assert "expiration_date>=current_date" in source


def test_superseded_pilots_are_archived_not_destroyed():
    source = (ROOT / "src/scripts/maintain_entry_exit_oos_admissions_v1.py").read_text()
    assert "adaptive_regime_paper_pilot_archive_v1" in source
    assert "RETURNING p.*" in source
