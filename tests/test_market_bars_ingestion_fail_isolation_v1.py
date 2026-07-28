from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_continuous_ingestion_runs_each_symbol_independently() -> None:
    source = (ROOT / "src/scripts/ingestion/run_continuous_market_bars_ingestion.py").read_text()
    assert "for symbol in symbols:" in source
    assert "run_backfill(symbol, tf" in source
    assert "load_watch_symbols()" in source


def test_backfill_skips_bad_symbol_without_aborting_batch() -> None:
    source = (ROOT / "src/scripts/ingestion/backfill_finam_futures_market_bars.py").read_text()
    assert "grpc.StatusCode.NOT_FOUND" in source
    assert "FINAM_FUTURES_MARKET_BARS_SYMBOL_SKIPPED" in source
    assert "failed_symbols.append(symbol)" in source
    assert "raise RuntimeError" not in source
    assert "return 1 if failed_symbols else 0" in source
