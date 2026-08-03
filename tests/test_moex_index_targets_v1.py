from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_index_ingestion_includes_extended_market_and_volatility_regime() -> None:
    source = (ROOT / "src/scripts/research/run_moex_index_backfill_v1.py").read_text()
    assert '"IMOEX2"' in source
    assert '"RVI"' in source
