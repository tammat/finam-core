from domain.regime.vol_target_sizer import VolatilityTargetSizer
from domain.regime.regime_detector import RegimeState, VolatilityRegime
from strategy.signal import Signal


def test_scales_down_when_vol_high():
    sizer = VolatilityTargetSizer(target_vol=1.0)

    regime = RegimeState(VolatilityRegime.HIGH, volatility=2.0)

    signal = Signal(symbol="NG", side="BUY", quantity=10)

    new_signal = sizer.apply(signal, regime)

    assert new_signal.quantity == 5


def test_scales_up_when_vol_low():
    sizer = VolatilityTargetSizer(target_vol=1.0)

    regime = RegimeState(VolatilityRegime.LOW, volatility=0.5)

    signal = Signal(symbol="NG", side="BUY", quantity=10)

    new_signal = sizer.apply(signal, regime)

    assert new_signal.quantity == 20


def test_clamped_multiplier():
    sizer = VolatilityTargetSizer(target_vol=1.0, max_multiplier=1.5)

    regime = RegimeState(VolatilityRegime.LOW, volatility=0.1)

    signal = Signal(symbol="NG", side="BUY", quantity=10)

    new_signal = sizer.apply(signal, regime)

    assert new_signal.quantity == 15  # capped