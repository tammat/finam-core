import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "src" / "scripts" / "run_finam_microstructure_ws_v1.py"
SPEC = importlib.util.spec_from_file_location("microstructure_ws", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_data_watchdog_trips_at_threshold() -> None:
    assert MODULE.data_is_stale(100.0, 189.9, 90.0) is False
    assert MODULE.data_is_stale(100.0, 190.0, 90.0) is True


def test_merge_symbols_normalizes_shadow_indices_and_deduplicates() -> None:
    assert MODULE.merge_symbols(
        ("SBER@MISX", "IMOEX"),
        ("IMOEX@MISX", "BRN6@RTSX"),
    ) == ("SBER@MISX", "IMOEX@MISX", "BRN6@RTSX")


def test_merge_symbols_applies_subscription_limit() -> None:
    assert MODULE.merge_symbols(("A", "B", "C"), limit=2) == ("A", "B")
