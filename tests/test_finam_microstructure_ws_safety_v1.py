import ast
from pathlib import Path


SOURCE = Path("src/scripts/run_finam_microstructure_ws_v1.py")


def test_finam_quote_sizes_support_actual_camel_case_payload() -> None:
    source = SOURCE.read_text()
    assert 'first_number(quote, "bidSize", "bid_size")' in source
    assert 'first_number(quote, "askSize", "ask_size")' in source


def _function(name: str):
    tree = ast.parse(SOURCE.read_text())
    return next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)


def test_expired_futures_are_filtered_before_subscription() -> None:
    source = SOURCE.read_text()
    assert "def contract_is_current" in source
    assert "contract_is_current(symbol)" in source
    assert 'MAX_DETAIL_SYMBOLS = int(os.getenv(' in source
    assert 'detail_symbols = symbols[:MAX_DETAIL_SYMBOLS]' in source
    assert "1+2*len(detail_symbols)" in source
    assert _function("contract_is_current")


def test_collector_permission_migration_covers_universe_and_sinks() -> None:
    sql = Path("sql/analytics/067_microstructure_collector_permissions_v1.sql").read_text()
    assert "forward_edge_shadow_trade_v1" in sql
    assert "market_data_watch_universe" in sql
    assert "market_microstructure_snapshot_v1" in sql
    assert "market_trade_tape_v1" in sql
