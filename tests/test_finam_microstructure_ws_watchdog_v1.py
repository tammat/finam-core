import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "src" / "scripts" / "run_finam_microstructure_ws_v1.py"
SPEC = importlib.util.spec_from_file_location("microstructure_ws", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_quote_size_parser_accepts_finam_camel_case_values() -> None:
    quote = {"bidSize": {"value": "201.0"}, "askSize": {"value": "5.0"}}
    assert MODULE.first_number(quote, "bidSize", "bid_size") == MODULE.Decimal("201.0")
    assert MODULE.first_number(quote, "askSize", "ask_size") == MODULE.Decimal("5.0")


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


def test_active_oos_has_priority_and_eight_detail_slots() -> None:
    source = SCRIPT.read_text()
    assert 'MAX_DETAIL_SYMBOLS", "8"' in source
    assert 'query("DYNAMIC_PRIORITY"' in source
    assert 'query("ACTIVE_OOS"' in source
    assert "analytics.futures_roll_decision_v1" in source
    assert "merge_symbols(active_oos, dynamic_priority, recent_fills" in source
    assert "analytics.microstructure_research_priority_v1" in source
    assert "selected_for_detail" in source
    assert 'PRIORITY_REFRESH_SECONDS' in source


def test_user_service_keeps_collector_autonomous() -> None:
    unit = SCRIPT.parents[2] / "deploy/systemd/user/finam-microstructure-ws.service"
    source = unit.read_text()
    assert "MARKETCORE_MICROSTRUCTURE_MAX_DETAIL_SYMBOLS=8" in source
    assert "Restart=always" in source
