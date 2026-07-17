from pathlib import Path

from scripts.edge_research_universe_v1 import category,select_diverse


ROOT=Path(__file__).resolve().parents[1]


def test_market_categories_cover_energy_and_core_assets():
    assert category("BRQ6@RTSX") == "OIL"
    assert category("NGQ6@RTSX") == "GAS"
    assert category("GDZ6@RTSX") == "METALS"
    assert category("CNYRUB_TOM@MISX") == "FX"
    assert category("IMOEX@MISX") == "INDEX"
    assert category("SBER@MISX") == "EQUITY"


def test_diverse_selection_reserves_oil_and_gas_slots():
    policy={
        "max_markets":6,
        "category_order":["OIL","GAS","METALS","FX","INDEX","EQUITY","OTHER"],
        "category_quotas":{"OIL":1,"GAS":1,"METALS":0,"FX":0,"INDEX":0,"EQUITY":4,"OTHER":0},
    }
    symbols=["SBER@MISX","GAZP@MISX","LKOH@MISX","VTBR@MISX","ROSN@MISX","T@MISX","BRQ6@RTSX","NGQ6@RTSX"]
    candidates=[{"symbol":symbol,"category_code":category(symbol)} for symbol in symbols]
    selected=select_diverse(candidates,policy)
    selected_symbols={item["symbol"] for item in selected}
    assert len(selected) == 6
    assert "BRQ6@RTSX" in selected_symbols
    assert "NGQ6@RTSX" in selected_symbols


def test_discovery_and_walkforward_use_shared_db_policy():
    for relative in (
        "src/scripts/build_edge_regime_hypothesis_discovery_v2.py",
        "src/scripts/build_walkforward_edge_search_v3.py",
    ):
        text=(ROOT/relative).read_text()
        assert "load_research_universe" in text
        assert "ORDER BY count(*) DESC LIMIT 12" not in text


def test_migration_records_selection_audit_and_russian_resources():
    text=(ROOT/"sql/analytics/096_diverse_research_universe_v1.sql").read_text()
    assert "edge_research_universe_policy_v1" in text
    assert "edge_research_universe_snapshot_v1" in text
    assert '"OIL":1' in text and '"GAS":1' in text
    assert "research.universe.reason.category_quota_selected" in text
    assert "Инструменты цикла" in text


def test_universe_excludes_expired_futures_and_is_visible_on_panel():
    selector=(ROOT/"src/scripts/edge_research_universe_v1.py").read_text()
    renderer=(ROOT/"src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py").read_text()
    assert "expiration_date)>=current_date" in selector
    assert "_universe_table(s.universe_items)" in renderer
