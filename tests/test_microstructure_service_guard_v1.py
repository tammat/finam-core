from pathlib import Path


def test_microstructure_wrapper_prevents_duplicates() -> None:
    source = Path("deploy/run-finam-microstructure-ws.sh").read_text()
    assert "runtime/locks/finam-microstructure-ws.lock" in source
    assert "flock -n 9" in source
    assert "PYTHONDONTWRITEBYTECODE=1" in source


def test_systemd_unit_is_restartable_and_fail_closed() -> None:
    source = Path("deploy/systemd/finam-microstructure-ws.service").read_text()
    assert "Restart=always" in source
    assert "REAL_TRADING_ENABLED" not in source
