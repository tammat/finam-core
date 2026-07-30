from decimal import Decimal
from pathlib import Path

from scripts.build_market_regime_context_v1 import asset_influence, market_state, variant_decision


def test_market_state_matrix() -> None:
    assert market_state("UP","LOW_VOL") == "RISK_ON"
    assert market_state("DOWN","HIGH_VOL") == "STRESS"
    assert market_state("RANGE","LOW_VOL") == "RANGE"


def test_variants_are_paired_and_advisory() -> None:
    signal={"symbol":"SBER@MISX","side":"BUY","strategy":"BREAKOUT"}
    context={"mx_trend":"UP","rvi_regime":"NORMAL_VOL"}
    assert variant_decision("BASELINE",signal,context)[0] == "INCLUDE"
    assert variant_decision("MX_FILTERED",signal,context)[0] == "INCLUDE"
    assert variant_decision("MX_RVI_FILTERED",signal,context)[0] == "INCLUDE"
    assert asset_influence("BRQ6@RTSX") == "WEAK"


def test_context_contract_has_no_execution_permission() -> None:
    sql=Path("sql/analytics/237_market_regime_context_v1.sql").read_text()
    script=Path("src/scripts/build_market_regime_context_v1.py").read_text()
    assert "parent_signal_id" in sql and "UNIQUE(parent_signal_id,variant_code)" in sql
    assert "paper_changed=0 real_changed=0" in script
    assert "current, prior" not in script


def test_ui_exposes_context_and_shadow_variants() -> None:
    resolver=Path("src/marketcore/presentation/workspace_v2/resolver/control_compact_v3_resolver.py").read_text()
    renderer=Path("src/marketcore/presentation/workspace_v2/renderer/control_compact_v3_domain_renderer.py").read_text()
    assert "market_regime_context" in resolver
    assert "market_regime_shadow_variants" in resolver
    assert "Состояние рынка и Shadow-варианты" in renderer
