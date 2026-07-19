from finam_core.execution.fill_persistence_service import FillPersistenceService


class _Repository:
    def __init__(self) -> None:
        self.filled = []

    def mark_filled(self, signal_id: str) -> None:
        self.filled.append(signal_id)


class _Attribution:
    def __init__(self, repository: _Repository, linked: bool) -> None:
        self.signal_repository = repository
        self.linked = linked

    def link_fill_from_payload(self, _fill) -> bool:
        return self.linked


class _Fill:
    fill_id = "fill-1"
    signal_id = None
    symbol = "SBERP@MISX"
    side = "BUY"
    qty = 1.0
    price = 100.0


def test_successful_attribution_marks_signal_filled() -> None:
    repository = _Repository()
    service = FillPersistenceService(
        attribution_service=_Attribution(repository, linked=True)
    )

    result = service.persist_fill(_Fill(), payload={"signal_id": "signal-1"})

    assert result["signal_linked"] is True
    assert result["signal_status"] == "FILLED"
    assert repository.filled == ["signal-1"]
