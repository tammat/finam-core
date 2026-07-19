from pathlib import Path

from finam_core.analytics.signal_repository import SignalRepository
from finam_core.pipelines.paper_pipeline import PaperTradingPipeline


ROOT = Path(__file__).resolve().parents[1]


class _LifecycleRepository:
    def __init__(self) -> None:
        self.accepted = []
        self.rejected = []

    def mark_accepted(self, signal_id: str) -> None:
        self.accepted.append(signal_id)

    def mark_rejected(self, signal_id: str, reason: str) -> None:
        self.rejected.append((signal_id, reason))


class _Cursor:
    def __init__(self) -> None:
        self.executions = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, query, params):
        self.executions.append((query, params))


class _Connection:
    def __init__(self) -> None:
        self.cursor_instance = _Cursor()
        self.committed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True


def test_pipeline_lifecycle_helpers_finalize_persisted_signal() -> None:
    pipeline = object.__new__(PaperTradingPipeline)
    repository = _LifecycleRepository()
    pipeline.signal_repository = repository
    intent = {"signal_id": "signal-1"}

    pipeline._reject_persisted_signal_v1(intent, "strict_edge_gate:no_match")
    pipeline._accept_persisted_signal_v1(intent)

    assert repository.rejected == [("signal-1", "strict_edge_gate:no_match")]
    assert repository.accepted == ["signal-1"]


def test_signal_repository_marks_admission_as_terminal_status() -> None:
    connection = _Connection()
    SignalRepository(connection).mark_accepted("signal-2")

    assert connection.committed is True
    query, params = connection.cursor_instance.executions[0]
    assert "UPDATE signals" in query
    assert params == ("RISK_ACCEPTED", None, "signal-2")


def test_known_post_persistence_gates_finalize_lifecycle() -> None:
    source = (ROOT / "src/finam_core/pipelines/paper_pipeline.py").read_text()
    post_save = source[source.index("intent[\"signal_id\"] = signal_id") : source.index("def generate(")]

    expected_reasons = {
        "runtime_strategy_blocked",
        "duplicate_signal",
        "strict_edge_gate",
        "risk_router",
        "cluster_block",
        "entry_gate",
        "execution_invalid_fill",
    }
    for reason in expected_reasons:
        assert f'"{reason}' in post_save or f'f"{reason}' in post_save

    assert "self._accept_persisted_signal_v1(intent)" in post_save
