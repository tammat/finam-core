from pathlib import Path


SOURCE=Path("src/marketcore/presentation/workspace_v2/presenter/home_v2_presenter.py").read_text(encoding="utf-8")


def test_clean_mode_is_default_and_reversible():
    assert 'MARKETCORE_HOME_CLEAN_MODE", "1"' in SOURCE
    assert "if clean_mode else" in SOURCE
    assert "profit_section, system_section, status_section" in SOURCE


def test_clean_home_keeps_only_current_process_groups():
    assert '(operating_section, operator_actions_section, operator_section)' in SOURCE
    assert '{"model_health", "edge_search", "signal_funnel", "diagnostic_funnels", "main_loss", "loss_solution"}' in SOURCE
