#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.data.finam_futures_signal_radar import FinamFuturesSignalRadar

radar = FinamFuturesSignalRadar()

buy = radar.build_signal(symbol="BRN6@RTSX", last=64.0, atr=1.0, trend_score=0.7)
assert buy is not None
assert buy.side == "BUY"
assert buy.stop_loss < buy.entry
assert buy.take_profit > buy.entry

sell = radar.build_signal(symbol="NGQ6@RTSX", last=3.5, atr=0.1, trend_score=-0.7)
assert sell is not None
assert sell.side == "SELL"
assert sell.stop_loss > sell.entry
assert sell.take_profit < sell.entry

flat = radar.build_signal(symbol="SiM6@RTSX", last=93450, atr=620, trend_score=0.1)
assert flat is None

print("FINAM_FUTURES_SIGNAL_RADAR_OK")
PY
