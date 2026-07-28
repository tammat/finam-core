from __future__ import annotations

from datetime import datetime, timedelta, timezone

from finam_core.regime.candle_regime_engine_v2 import CandleBarV2, CandleRegimeEngineV2


def _bars(*, count: int = 180, step: float = 0.25, spread: float = 1.0, end=None):
    end = end or datetime.now(timezone.utc) - timedelta(minutes=5)
    start = end - timedelta(minutes=5 * (count - 1))
    bars = []
    price = 100.0
    for index in range(count):
        close = price + step
        bars.append(CandleBarV2(start + timedelta(minutes=5 * index), price, close + spread, price - spread, close, 1000.0))
        price = close
    return bars


def test_regime_uses_real_candle_atr_without_two_percent_cap():
    engine = CandleRegimeEngineV2("postgresql:///unused")
    decision = engine.classify("BRQ6@RTSX", "M5", _bars(spread=8.0))
    assert decision.atr_pct > 0.02
    assert decision.source_version == "CANDLE_REGIME_V3"


def test_regime_requires_three_matching_closed_bars():
    engine = CandleRegimeEngineV2("postgresql:///unused")
    bars = _bars()
    confirmed = engine.classify("SBER@MISX", "M5", bars)
    assert confirmed.confirmed_bars == 3

    last = bars[-1]
    bars[-1] = CandleBarV2(last.ts, last.open, last.high + 30, last.low - 30, last.close - 20, last.volume)
    changed = engine.classify("SBER@MISX", "M5", bars)
    assert changed.confirmed_bars == 0
    assert not changed.is_tradeable()


def test_regime_marks_stale_series_untradeable():
    engine = CandleRegimeEngineV2("postgresql:///unused")
    old_end = datetime.now(timezone.utc) - timedelta(hours=2)
    decision = engine.classify("NGQ6@RTSX", "M5", _bars(end=old_end))
    assert decision.stale
    assert not decision.is_tradeable()


def test_cache_identity_is_instrument_and_timeframe():
    engine = CandleRegimeEngineV2("postgresql:///unused")
    engine._cache[("SBER@MISX", "M5")] = (0.0, engine.classify("SBER@MISX", "M5", _bars()))
    engine._cache[("SBER@MISX", "M15")] = (0.0, engine.classify("SBER@MISX", "M15", _bars()))
    engine._cache[("BRQ6@RTSX", "M5")] = (0.0, engine.classify("BRQ6@RTSX", "M5", _bars()))
    assert len(engine._cache) == 3


def test_v4_migration_preserves_v3_and_requires_regime_source():
    sql = open("sql/analytics/199_fresh_v4_candle_regime_cohort_v1.sql", encoding="utf-8").read()
    assert "FRESH_V4_REGIME_EQUITY" in sql
    assert "FRESH_V4_REGIME_FUTURES" in sql
    assert "CANDLE_REGIME_V2" in sql


def test_v5_migration_requires_confirmed_regime_v3():
    sql = open(
        "sql/analytics/206_fresh_v5_confirmed_regime_cohort_v1.sql",
        encoding="utf-8",
    ).read()
    assert "FRESH_V5_CONFIRMED_EQUITY" in sql
    assert "FRESH_V5_CONFIRMED_FUTURES" in sql
    assert "CANDLE_REGIME_V3" in sql
    assert "regime_confirmed_bars" in sql
    assert "FRESH_V3" in sql
