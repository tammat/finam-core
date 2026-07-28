from finam_core.regime.regime_labeler import RegimeLabeler


def test_preserves_confirmed_normal_volatility() -> None:
    assert (
        RegimeLabeler.label(
            features={"trend": "down", "volatility": "normal_vol"}
        )
        == "trend_down_normal_vol"
    )


def test_derives_normal_volatility_from_midrange_atr() -> None:
    assert (
        RegimeLabeler.label(
            features={"trend": "range", "atr_pct": 0.01}
        )
        == "range_normal_vol"
    )
