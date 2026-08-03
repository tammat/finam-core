from datetime import datetime, timezone

from finam_core.analytics.signal_repository import completed_bar_signal_id_v1


def test_completed_bar_id_ignores_quote_and_wall_clock_changes() -> None:
    base = {
        "symbol": "SBER@MISX",
        "strategy": "MEAN_REVERSION_EQUITY",
        "side": "BUY",
        "timeframe": "M5",
        "price": 278.10,
        "features": {"regime_bar_ts": datetime(2026, 8, 3, 4, 30, tzinfo=timezone.utc)},
    }
    later_quote = {**base, "price": 279.25, "signal_id": "wall-clock-specific"}
    assert completed_bar_signal_id_v1(base) == completed_bar_signal_id_v1(later_quote)


def test_completed_bar_id_separates_side_and_bar() -> None:
    base = {
        "symbol": "SBER@MISX", "strategy": "MEAN_REVERSION_EQUITY",
        "side": "BUY", "timeframe": "M5",
        "features": {"regime_bar_ts": "2026-08-03T04:30:00+00:00"},
    }
    sell = {**base, "side": "SELL"}
    next_bar = {**base, "features": {"regime_bar_ts": "2026-08-03T04:35:00+00:00"}}
    assert completed_bar_signal_id_v1(base) != completed_bar_signal_id_v1(sell)
    assert completed_bar_signal_id_v1(base) != completed_bar_signal_id_v1(next_bar)


def test_completed_bar_id_canonicalizes_datetime_and_iso_text() -> None:
    base = {
        "symbol": "SBER@MISX", "strategy": "MEAN_REVERSION_EQUITY",
        "side": "BUY", "timeframe": "M5",
        "features": {"regime_bar_ts": datetime(2026, 8, 3, 4, 30, tzinfo=timezone.utc)},
    }
    as_text = {**base, "features": {"regime_bar_ts": "2026-08-03T04:30:00+00:00"}}
    assert completed_bar_signal_id_v1(base) == completed_bar_signal_id_v1(as_text)


def test_pipeline_stops_duplicate_before_risk_and_shadow_gates() -> None:
    source = open("src/finam_core/pipelines/paper_pipeline.py", encoding="utf-8").read()
    assert source.count('intent.pop("_signal_persisted_new", True)') >= 3
    assert "PIPE_COMPLETED_BAR_SIGNAL_DUPLICATE" in source
    assert "PIPE_PRE_SIGNAL_SHADOW_DEDUP" in source
