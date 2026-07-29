from finam_core.analytics.futures_risk_calibrator import (
    CalibrationBounds,
    TradePathObservation,
    calibrate_profile,
)


def test_insufficient_data_does_not_recommend():
    result = calibrate_profile(
        [TradePathObservation(True, 1.0, 3.0, 1.4)] * 10,
        CalibrationBounds(1.2, 2.0, 2.5, 1.5, 1.3),
    )
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["recommended_stop_atr"] is None


def test_ready_sample_uses_mae_mfe_and_bounds():
    observations = [
        TradePathObservation(index < 12, 0.5 + index * 0.05, 2.0 + index * 0.1, 1.2 + index * 0.02)
        for index in range(20)
    ]
    result = calibrate_profile(
        observations,
        CalibrationBounds(1.2, 2.0, 2.5, 1.5, 1.3),
    )
    assert result["status"] == "ADVISORY_READY"
    assert 1.2 <= result["recommended_stop_atr"] <= 2.0
    assert result["recommended_take_atr"] >= 1.5 * result["recommended_stop_atr"]
    assert result["recommended_volume_ratio"] >= 1.0
