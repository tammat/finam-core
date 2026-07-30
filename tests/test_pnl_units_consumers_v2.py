from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_optimizer_and_calibrator_require_verified_rub_units():
    optimizer = (ROOT / "src/scripts/analytics/build_entry_exit_optimizer_v1.py").read_text()
    calibration = (ROOT / "src/scripts/analytics/build_futures_risk_calibration_v1.py").read_text()
    assert "PNL_UNITS_V2_RUB" in optimizer
    assert "PNL_UNITS_V2_RUB" in calibration


def test_ui_uses_canonical_closed_pnl_and_contract_units_for_active_positions():
    resolver = (ROOT / "src/marketcore/presentation/workspace_v2/resolver/control_compact_v3_resolver.py").read_text()
    assert "c.net_pnl AS net_pnl" in resolver
    assert "PNL_UNITS_V2_RUB" in resolver
    assert "ms.tick_value/ms.tick_size" in resolver
    assert "ELSE ms.lot_size END" in resolver
