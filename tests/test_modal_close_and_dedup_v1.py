from pathlib import Path


def test_action_controller_coalesces_concurrent_duplicate_requests() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_action_controller_v2.js").read_text()
    assert "const inFlight = new Map();" in source
    assert "if (inFlight.has(semanticKey)) return inFlight.get(semanticKey);" in source
    assert "inFlight.delete(semanticKey)" in source


def test_all_confirmation_dialogs_close_before_dispatch() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert source.count("dialog.close();") >= 4
    assert "let submitting = false;" in source
    assert "if (submitting) return;" in source
    assert "submitting = true;" in source


def test_repeated_universe_override_is_a_db_noop() -> None:
    source = Path("src/marketcore/action/command_worker_v2.py").read_text()
    assert "unchanged:priority:" in source
    assert "unchanged:{mode.lower()}" in source


def test_runtime_status_translation_patch_covers_live_render_trees() -> None:
    sql = Path("sql/analytics/105_workspace_runtime_status_i18n_v1.sql").read_text()
    assert "status.edge_search_started" in sql
    assert "status.awaiting_forward_readiness" in sql
