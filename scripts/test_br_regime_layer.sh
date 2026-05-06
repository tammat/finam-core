#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.strategy.br_regime_layer import BRRegimeLayer

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
)
assert d.allowed is True
assert d.regime == "compression"
assert d.confirmation_required is True
assert d.size_multiplier == 0.5


from types import SimpleNamespace
from finam_core.pipelines.paper_pipeline import PaperTradingPipeline
from finam_core.strategy.br_regime_layer import BRRegimeLayer

class DummyPipeline:
    br_regime_layer = BRRegimeLayer()

ok_signal = SimpleNamespace(
    symbol="BRM6@RTSX",
    side="BUY",
    price=110.0,
    features={"atr_pct": 0.01, "slope_m5": 0.001, "slope_m15": 0.001, "compression_ratio": 0.9},
)
ok_decision = PaperTradingPipeline._br_regime_allows_signal(DummyPipeline(), ok_signal)
assert ok_decision.allowed is True, ok_decision

bad_signal = SimpleNamespace(
    symbol="BRM6@RTSX",
    side="SELL",
    price=110.0,
    features={"atr_pct": 0.01, "slope_m5": 0.001, "slope_m15": 0.001, "compression_ratio": 0.9},
)
bad_decision = PaperTradingPipeline._br_regime_allows_signal(DummyPipeline(), bad_signal)
assert bad_decision.allowed is False, bad_decision
assert bad_decision.regime == "misaligned", bad_decision

print("BR_REGIME_LAYER_OK")
PY
