from domain.regime.drawdown_vol_sizer import DrawdownAdaptiveVolSizer
from domain.regime.regime_detector import RegimeState, VolatilityRegime
from strategy.signal import Signal


class DummyPortfolio:
    def __init__(self, starting_cash, equity):
        self.starting_cash = starting_cash
        self.equity = equity


def test_no_drawdown_no_scaling():
    sizer = DrawdownAdaptiveVolSizer(base_target_vol=1.0)

    regime = RegimeState(VolatilityRegime.NORMAL, volatility=1.0)
    signal = Signal(symbol="NG", side="BUY", quantity=10)

    portfolio = DummyPortfolio(100_000, 100_000)

    new_signal = sizer.apply(signal, regime, portfolio=portfolio)

    assert new_signal.quantity == 10


def test_drawdown_reduces_size():
    sizer = DrawdownAdaptiveVolSizer(base_target_vol=1.0)

    regime = RegimeState(VolatilityRegime.NORMAL, volatility=1.0)
    signal = Signal(symbol="NG", side="BUY", quantity=10)

    portfolio = DummyPortfolio(100_000, 85_000)  # 15% DD

    new_signal = sizer.apply(signal, regime, portfolio=portfolio)

    assert new_signal.quantity < 10


def test_min_factor_floor():
    sizer = DrawdownAdaptiveVolSizer(
        base_target_vol=1.0,
        dd_threshold=0.05,
        min_factor=0.4,
    )

    regime = RegimeState(VolatilityRegime.NORMAL, volatility=1.0)
    signal = Signal(symbol="NG", side="BUY", quantity=10)

    portfolio = DummyPortfolio(100_000, 50_000)  # huge DD

    new_signal = sizer.apply(signal, regime, portfolio=portfolio)

    assert new_signal.quantity >= 4  # 10 * 0.4