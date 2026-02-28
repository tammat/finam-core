# tests/test_regime_detector.py

from domain.regime.regime_detector import (
    RegimeDetector,
    VolatilityRegime,
)


def test_low_volatility():
    detector = RegimeDetector(window=5, low_threshold=0.5, high_threshold=2.0)

    prices = [100, 100.1, 100.2, 100.1, 100.15]

    state = detector.detect(prices)

    assert state.regime == VolatilityRegime.LOW


def test_high_volatility():
    detector = RegimeDetector(window=5, low_threshold=0.5, high_threshold=1.0)

    prices = [100, 105, 95, 110, 90]

    state = detector.detect(prices)

    assert state.regime == VolatilityRegime.HIGH


def test_normal_volatility():
    detector = RegimeDetector(window=5, low_threshold=0.1, high_threshold=5.0)

    prices = [100, 101, 99, 102, 98]

    state = detector.detect(prices)

    assert state.regime == VolatilityRegime.NORMAL


def test_insufficient_history():
    detector = RegimeDetector(window=10)

    prices = [100, 101]

    state = detector.detect(prices)

    assert state.regime == VolatilityRegime.NORMAL
    assert state.volatility == 0.0