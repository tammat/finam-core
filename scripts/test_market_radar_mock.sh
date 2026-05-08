#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.data.market_radar import MarketRadar

data = {
    "securities": {
        "columns": ["SECID", "SHORTNAME"],
        "data": [
            ["SBER", "Сбербанк"],
            ["GAZP", "Газпром"],
            ["PLZL", "Полюс"],
        ],
    },
    "marketdata": {
        "columns": ["SECID", "LAST", "CHANGE", "VALTODAY", "VOLTODAY", "NUMTRADES"],
        "data": [
            ["SBER", 320.0, 1.7, 5_000_000_000, 10_000_000, 50000],
            ["GAZP", 130.0, -2.2, 3_000_000_000, 8_000_000, 45000],
            ["PLZL", 2300.0, 0.4, 10_000_000, 1000, 50],
        ],
    },
}

radar = MarketRadar(min_value_today=50_000_000)
result = radar.build(data, top_n=5)

assert result["gainers"][0].symbol == "SBER@MISX", result
assert result["losers"][0].symbol == "GAZP@MISX", result

print("MARKET_RADAR_MOCK_OK")
PY
