from pathlib import Path
from types import SimpleNamespace

from marketcore.action.command_worker_v2 import COMMANDS, SafeSubprocessCommandExecutorV2
from scripts.run_marketcore_governed_command_worker_v2 import scheduled_request_kinds


ROOT = Path(__file__).resolve().parents[1]


def test_installed_research_worker_routes_edge_requests_first() -> None:
    assert scheduled_request_kinds("RESEARCH_REFRESH") == (
        "EDGE_SEARCH_RUN",
        "RESEARCH_REFRESH",
    )


def test_other_worker_filters_are_not_broadened() -> None:
    assert scheduled_request_kinds("PAPER_OBSERVATION") == ("PAPER_OBSERVATION",)
    assert scheduled_request_kinds(None) == (None,)


def test_full_edge_cycle_timeout_covers_measured_cycle_duration() -> None:
    source = (ROOT / "src/marketcore/action/command_worker_v2.py").read_text()
    assert '"live_allowed=0"), 10800' in source


def test_resource_guard_is_a_safe_terminal_result() -> None:
    worker = (ROOT / "src/marketcore/action/command_worker_v2.py").read_text()
    runner = (ROOT / "src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    assert "VERDICT=AUTONOMOUS_EDGE_SEARCH_RESOURCE_GUARD_OK" in worker
    assert 'print("live_allowed=0")' in runner
    assert 'print("VERDICT=AUTONOMOUS_EDGE_SEARCH_CYCLE_V1_OK")' in runner
    assert "VERDICT=AUTONOMOUS_EDGE_SEARCH_CHECKPOINTED" in worker


def test_executor_accepts_resource_guard_without_accepting_arbitrary_output(monkeypatch) -> None:
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: SimpleNamespace(
        returncode=0,
        stdout="live_allowed=0\nVERDICT=AUTONOMOUS_EDGE_SEARCH_RESOURCE_GUARD_OK\n",
        stderr="",
    ))
    assert SafeSubprocessCommandExecutorV2().execute(COMMANDS["EDGE_SEARCH_RUN"]) == (
        "VERDICT=AUTONOMOUS_EDGE_SEARCH_RESOURCE_GUARD_OK"
    )


def test_executor_accepts_durable_discovery_checkpoint(monkeypatch) -> None:
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: SimpleNamespace(
        returncode=0,
        stdout="live_allowed=0\nVERDICT=AUTONOMOUS_EDGE_SEARCH_CHECKPOINTED\n",
        stderr="",
    ))
    assert SafeSubprocessCommandExecutorV2().execute(COMMANDS["EDGE_SEARCH_RUN"]) == (
        "VERDICT=AUTONOMOUS_EDGE_SEARCH_CHECKPOINTED"
    )
