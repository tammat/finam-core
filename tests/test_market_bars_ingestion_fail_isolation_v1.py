from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[1]


def test_continuous_ingestion_runs_each_target_independently() -> None:
    source = (ROOT / "src/scripts/ingestion/run_continuous_market_bars_ingestion.py").read_text()
    assert "for symbol, timeframe in targets:" in source
    assert "run_backfill(symbol, timeframe" in source
    assert "load_watch_targets()" in source


def test_continuous_ingestion_honours_watch_timeframe_and_skips_missing_mic() -> None:
    source = (ROOT / "src/scripts/ingestion/run_continuous_market_bars_ingestion.py").read_text()
    assert "SELECT symbol, timeframe" in source
    assert "valid_finam_symbol(symbol)" in source
    assert "reason=MISSING_MIC" in source


def test_continuous_ingestion_prioritises_clean_v5_cohort() -> None:
    source = (ROOT / "src/scripts/ingestion/run_continuous_market_bars_ingestion.py").read_text()
    assert "V5_FRESHNESS_PRIORITY" in source
    assert "array_position(%s::text[], symbol) NULLS LAST" in source
    for symbol in ("BRQ6@RTSX", "NGQ6@RTSX", "SBER@MISX", "GAZP@MISX", "LKOH@MISX", "NVTK@MISX", "VTBR@MISX"):
        assert symbol in source


def test_exact_target_specs_do_not_create_timeframe_cross_product() -> None:
    path = ROOT / "src/scripts/ingestion/run_continuous_market_bars_ingestion.py"
    spec = importlib.util.spec_from_file_location("continuous_bars", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.parse_target_specs(
        "BRQ6@RTSX=M1,NGQ6@RTSX=M1,NVTK@MISX=M5"
    ) == [
        ("BRQ6@RTSX", "M1"),
        ("NGQ6@RTSX", "M1"),
        ("NVTK@MISX", "M5"),
    ]


def test_backfill_skips_bad_symbol_without_aborting_batch() -> None:
    source = (ROOT / "src/scripts/ingestion/backfill_finam_futures_market_bars.py").read_text()
    assert "grpc.StatusCode.NOT_FOUND" in source
    assert "FINAM_FUTURES_MARKET_BARS_SYMBOL_SKIPPED" in source
    assert "failed_symbols.append(symbol)" in source
    assert "raise RuntimeError" not in source
    assert "return 1 if failed_symbols else 0" in source
