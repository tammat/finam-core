import inspect

from data.history_loader import HistoryLoader as H1
from finam_core.ingestion.history_loader import HistoryLoader as H2


def test_history_loader_alias():
    assert H1 is H2
    assert "finam_core/ingestion/history_loader.py" in inspect.getfile(H1)
