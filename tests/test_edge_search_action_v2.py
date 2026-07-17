from pathlib import Path

from marketcore.action.command_worker_v2 import COMMANDS
from marketcore.action.handler_registry_v2 import resolve_state_changing_action_v2


def test_edge_search_action_runs_full_safe_cycle() -> None:
    definition = resolve_state_changing_action_v2("research.edge_search.run")
    command = COMMANDS[definition.request_kind]
    assert definition.command_code == "RESEARCH.RUN_EDGE_SEARCH"
    assert command.argv[-1] == "src/scripts/run_autonomous_edge_search_cycle_v1.py"
    assert "VERDICT=AUTONOMOUS_EDGE_SEARCH_CYCLE_V1_OK" in command.expected_markers
    assert "live_allowed=0" in command.expected_markers


def test_research_page_exposes_edge_search_button() -> None:
    renderer = Path("src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py").read_text()
    controller = Path("src/marketcore/presentation/action_http_controller_v2.py").read_text()
    assert 'message_key="research.action.run_edge_search"' in renderer
    assert '"research.edge_search.run",ActionKindV2.COMMAND' in renderer
    assert 'definition.request_kind == "EDGE_SEARCH_RUN"' in controller
    assert "_start_async_command_worker(request_id)" in controller
    resolver = Path("src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py").read_text()
    assert "edge_search_cycle_status_v1" in resolver
    assert 'edge_search_status' in renderer


def test_command_request_schema_allows_edge_search() -> None:
    migration = Path("sql/marketcore_action/006_edge_search_command_v2.sql").read_text()
    assert "'EDGE_SEARCH_RUN'" in migration
    assert "'RESEARCH.RUN_EDGE_SEARCH'" in migration


def test_research_and_home_show_trusted_algorithm_results() -> None:
    resolver = Path("src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py").read_text()
    renderer = Path("src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py").read_text()
    home = Path("src/marketcore/presentation/workspace_v2/resolver/home_operator_dashboard_resolver_v1.py").read_text()
    assert "WALKFORWARD_EDGE_SEARCH_V4_TRUSTED_BARS" in resolver
    assert "research.algorithms.table" in renderer
    assert 'columns=("algorithm","markets","variants","folds","pf","passes","status","reason")' in renderer
    assert 'key=f"research.algorithm.column.{code}"' in renderer
    assert "WALKFORWARD_EDGE_SEARCH_V4_TRUSTED_BARS" in home
    assert '"algorithms": algorithms' in home
