#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from types import SimpleNamespace

from finam_core.strategy.br_regime_layer import BRRegimeLayer
from finam_core.pipelines.paper_pipeline import PaperTradingPipeline
from finam_core.features.volume_features import BarVolumeFeatureEngine


r = BRRegimeLayer()

d = r.evaluate(
    atr_pct=0.01,
    slope_m5=0.001,
    slope_m15=0.001,
    compression_ratio=0.9,
    signal_side="BUY",
)
assert d.allowed is True
assert d.regime == "trend_expansion_up"
assert d.confirmation_required is False

d = r.evaluate(
    atr_pct=0.0005,
    slope_m5=0.001,
    slope_m15=0.001,
    compression_ratio=0.9,
    signal_side="BUY",
)
assert d.allowed is False
assert d.regime == "dead_market"

d = r.evaluate(
    atr_pct=0.01,
    slope_m5=0.001,
    slope_m15=0.001,
    compression_ratio=0.9,
    signal_side="SELL",
)
assert d.allowed is False
assert d.regime == "misaligned"

d = r.evaluate(
    atr_pct=0.01,
    slope_m5=0.001,
    slope_m15=0.001,
    compression_ratio=0.4,
    signal_side="BUY",
    price=110.0,
    atr_short=0.5,
    atr_long=1.0,
)
assert d.allowed is True
assert d.regime == "compression"
assert d.confirmation_required is True
assert d.size_multiplier == 0.5
assert d.confirmation_ticks == 3
assert d.breakout_k == 0.8

d = r.evaluate(
    atr_pct=0.01,
    slope_m5=0.001,
    slope_m15=0.001,
    compression_ratio=1.5,
    signal_side="BUY",
    price=110.0,
    atr_short=1.5,
    atr_long=1.0,
)
assert d.allowed is True
assert d.regime == "volatility_expansion_up"
assert d.size_multiplier == 1.0
assert d.confirmation_ticks == 2
assert d.breakout_k == 1.2


class DummyPipeline:
    br_regime_layer = BRRegimeLayer()
    br_volume_features = BarVolumeFeatureEngine(lookback=5, confirm_ratio=1.5)

    def __init__(self):
        self.events = []
        self._br_volume_bars_by_symbol = {}

    def _append_br_volume_bar(self, symbol: str, price: float, volume=None):
        buf = self._br_volume_bars_by_symbol.setdefault(symbol, [])
        buf.append({"close": float(price), "volume": float(volume or 0.0)})
        return buf

    def _log_br_event(self, event_type, symbol, payload):
        self.events.append((event_type, symbol, payload))


ok_signal = SimpleNamespace(
    symbol="BRM6@RTSX",
    side="BUY",
    price=110.0,
    features={"atr_pct": 0.01, "slope_m5": 0.001, "slope_m15": 0.001, "compression_ratio": 0.9, "volume": 200.0},
)
pipe = DummyPipeline()
ok_decision = PaperTradingPipeline._br_regime_allows_signal(pipe, ok_signal)
assert ok_decision.allowed is True
assert any(x[0] == "BR_REGIME_DECISION" for x in pipe.events), pipe.events
assert any("rel_volume" in x[2] for x in pipe.events), pipe.events

bad_signal = SimpleNamespace(
    symbol="BRM6@RTSX",
    side="SELL",
    price=110.0,
    features={"atr_pct": 0.01, "slope_m5": 0.001, "slope_m15": 0.001, "compression_ratio": 0.9, "volume": 200.0},
)
pipe = DummyPipeline()
bad_decision = PaperTradingPipeline._br_regime_allows_signal(pipe, bad_signal)
assert bad_decision.allowed is False
assert bad_decision.regime == "misaligned"
assert any(x[0] == "BR_REGIME_DECISION" for x in pipe.events), pipe.events
assert any("rel_volume" in x[2] for x in pipe.events), pipe.events

print("BR_REGIME_LAYER_OK")
PY
