from pathlib import Path
import importlib.util
import sys


ROOT = Path(__file__).resolve().parents[1]
RESOLVER = ROOT / "src/marketcore/presentation/workspace_v2/resolver/control_compact_v3_resolver.py"
RENDERER = ROOT / "src/marketcore/presentation/workspace_v2/renderer/control_compact_v3_domain_renderer.py"
MIGRATION = ROOT / "sql/analytics/216_v5_evidence_driven_runtime_priority_v1.sql"


def test_control_center_exposes_closed_bar_position_diagnostics() -> None:
    source = RESOLVER.read_text()
    assert "open_position_diagnostics" in source
    assert "bars_held" in source
    assert "WAITING_FIRST_CLOSED_BAR" in source
    assert "SESSION_IDLE_OR_DATA_STALE" in source
    assert "CANDLE_EXIT_MONITOR_ACTIVE" in source


def test_open_position_diagnostics_add_no_operator_buttons() -> None:
    source = RENDERER.read_text()
    body = source[source.index("def _open_positions_section"):source.index("def _ru_status")]
    assert "RenderActionV2" not in body
    assert "_command(" not in body
    assert "баров" in body


def test_disabled_research_command_has_required_block_reason() -> None:
    spec = importlib.util.spec_from_file_location("control_v3_renderer", RENDERER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    node = module._command(
        "edge_run", "Запустить edge search", "research.edge_search.run",
        "RESEARCH.RUN_EDGE_SEARCH", enabled=False,
    )
    assert node.action.enabled is False
    assert node.action.blocked_reason_code == "RESEARCH_COMMAND_ALREADY_ACTIVE"


def test_runtime_priority_is_exact_fresh_v5_only() -> None:
    sql = MIGRATION.read_text()
    assert "h.cohort_code='FRESH_V5_CONFIRM'" in sql
    assert "h.level_code='EXACT_CONTEXT'" in sql
    assert "EARLY_STOP" not in sql.split("decision_code IN", 1)[1].split(")", 1)[0]
