from domain.regime.position_sizer import RegimePositionSizer
from domain.regime.regime_detector import RegimeState, VolatilityRegime


def test_low_regime_scales_up():
    sizer = RegimePositionSizer()
    regime = RegimeState(VolatilityRegime.LOW, 0.1)

    qty = sizer.scale(10, regime)

    assert qty == 12  # 10 * 1.2


def test_high_regime_scales_down():
    sizer = RegimePositionSizer()
    regime = RegimeState(VolatilityRegime.HIGH, 5.0)

    qty = sizer.scale(10, regime)

    assert qty == 5  # 10 * 0.5


def test_normal_regime_no_change():
    sizer = RegimePositionSizer()
    regime = RegimeState(VolatilityRegime.NORMAL, 1.0)

    qty = sizer.scale(10, regime)

    assert qty == 10