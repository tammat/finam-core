from scripts.check_market_open_readiness_v1 import quotes_are_fresh


def test_m1_is_the_fast_quote_liveness_probe() -> None:
    assert quotes_are_fresh(120, 700)
    assert not quotes_are_fresh(181, 700)


def test_m5_age_includes_the_five_minute_bar_duration() -> None:
    assert quotes_are_fresh(None, 479)
    assert not quotes_are_fresh(None, 481)


def test_missing_quote_stream_is_not_fresh() -> None:
    assert not quotes_are_fresh(None, None)
