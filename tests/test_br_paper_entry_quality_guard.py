from datetime import datetime, timezone
from types import SimpleNamespace

import psycopg

from finam_core.pipelines.paper_pipeline import PaperTradingPipeline


def _pipeline(*, slope=0.0, trend="range"):
    pipeline = PaperTradingPipeline.__new__(PaperTradingPipeline)
    decision = SimpleNamespace(
        source_version="CANDLE_REGIME_V3",
        data_ready=True,
        stale=False,
        confirmed_bars=3,
        bar_ts=datetime(2026, 7, 29, 19, 20, tzinfo=timezone.utc),
        normalized_slope=slope,
        trend=trend,
    )
    pipeline.candle_regime_engine_v2 = SimpleNamespace(evaluate=lambda *_: decision)
    return pipeline


class _Connection:
    def __init__(self, row):
        self.row = row

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, *_args, **_kwargs):
        return SimpleNamespace(fetchone=lambda: self.row)


def test_br_long_blocks_negative_confirmed_slope(monkeypatch):
    monkeypatch.setenv("BR_PAPER_ENTRY_QUALITY_GUARD_ENABLED", "1")
    pipeline = _pipeline(slope=-0.03)
    allowed, reason = pipeline._br_paper_entry_quality_allows_v1("BRQ6@RTSX", "BUY")
    assert not allowed
    assert reason.startswith("BR_LONG_SLOPE_NOT_CONFIRMED")


def test_br_blocks_until_three_closed_m5_bars_after_regime_exit(monkeypatch):
    monkeypatch.setenv("BR_PAPER_ENTRY_QUALITY_GUARD_ENABLED", "1")
    monkeypatch.setenv("BR_REGIME_EXIT_COOLDOWN_BARS", "3")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")
    monkeypatch.setattr(psycopg, "connect", lambda *_args, **_kwargs: _Connection({
        "exit_ts": datetime(2026, 7, 29, 19, 5, tzinfo=timezone.utc),
        "regime_bar_ts": datetime(2026, 7, 29, 19, 0, tzinfo=timezone.utc),
        "closed_bars_after_exit": 2,
    }))
    allowed, reason = _pipeline(slope=0.03)._br_paper_entry_quality_allows_v1("BRQ6@RTSX", "BUY")
    assert not allowed
    assert reason == "BR_REGIME_EXIT_COOLDOWN:2/3_M5_BARS"


def test_br_allows_new_confirmed_bar_after_cooldown(monkeypatch):
    monkeypatch.setenv("BR_PAPER_ENTRY_QUALITY_GUARD_ENABLED", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")
    monkeypatch.setattr(psycopg, "connect", lambda *_args, **_kwargs: _Connection({
        "exit_ts": datetime(2026, 7, 29, 19, 4, tzinfo=timezone.utc),
        "regime_bar_ts": datetime(2026, 7, 29, 19, 0, tzinfo=timezone.utc),
        "closed_bars_after_exit": 3,
    }))
    allowed, reason = _pipeline(slope=0.03)._br_paper_entry_quality_allows_v1("BRQ6@RTSX", "BUY")
    assert allowed
    assert reason.startswith("BR_ENTRY_QUALITY_PASS")


def test_br_blocks_consumed_signal_bar_fingerprint(monkeypatch):
    monkeypatch.setenv("BR_PAPER_ENTRY_QUALITY_GUARD_ENABLED", "1")
    pipeline = _pipeline(slope=0.03)
    pipeline._br_consumed_entry_bar_fingerprints_v1 = {
        "BRQ6@RTSX:BUY:2026-07-29T19:20:00+00:00"
    }
    allowed, reason = pipeline._br_paper_entry_quality_allows_v1("BRQ6@RTSX", "BUY")
    assert not allowed
    assert reason == "BR_DUPLICATE_REGIME_BAR_FINGERPRINT"


def test_non_br_is_unchanged():
    pipeline = PaperTradingPipeline.__new__(PaperTradingPipeline)
    assert pipeline._br_paper_entry_quality_allows_v1("SBER@MISX", "BUY") == (
        True,
        "BR_ENTRY_QUALITY_NOT_APPLICABLE",
    )


class _LifecycleRepo:
    def __init__(self, stop):
        self.stop = stop
        self.saved = None

    def load_state(self, **_kwargs):
        return {"current_stop": self.stop}

    def upsert_state(self, **kwargs):
        self.saved = kwargs


def test_all_instruments_keep_long_stop_monotonic(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    pipeline = PaperTradingPipeline.__new__(PaperTradingPipeline)
    pipeline.position_lifecycle_state_repository = _LifecycleRepo(101.0)
    pipeline._position_qty_for_symbol = lambda _symbol: 1.0
    pipeline._save_position_lifecycle_state(symbol="SBER@MISX", current_stop=99.0)
    assert pipeline.position_lifecycle_state_repository.saved["current_stop"] == 101.0


def test_all_instruments_keep_short_stop_monotonic(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    pipeline = PaperTradingPipeline.__new__(PaperTradingPipeline)
    pipeline.position_lifecycle_state_repository = _LifecycleRepo(101.0)
    pipeline._position_qty_for_symbol = lambda _symbol: -1.0
    pipeline._save_position_lifecycle_state(symbol="NGQ6@RTSX", current_stop=103.0)
    assert pipeline.position_lifecycle_state_repository.saved["current_stop"] == 101.0
