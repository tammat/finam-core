#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.data.market_radar import MarketRadar

radar = MarketRadar(
    min_value_today=50_000_000,
    min_abs_change_pct=0.5,
    max_abs_change_pct=20.0,
)

data = {
    "securities": {
        "columns": ["SECID", "SHORTNAME"],
        "data": [
            ["SBER", "Сбербанк"],
            ["LQDT", "ETF"],
            ["PLZL", "Полюс"],
        ],
    },
    "marketdata": {
        "columns": ["SECID", "LAST", "CHANGE", "VALTODAY", "VOLTODAY", "NUMTRADES"],
        "data": [
            ["SBER", 320, 2.0, 5_000_000_000, 1, 50000],
            ["LQDT", 1.0, 0.01, 5_000_000_000, 1, 50000],
            ["PLZL", 2000, -55.0, 5_000_000_000, 1, 50000],
        ],
    },
}

res = radar.build(data, imoex_change_pct=1.0)

assert len(res["gainers"]) == 1
assert res["gainers"][0].symbol == "SBER@MISX"

assert len(res["anomalies"]) == 1
assert res["anomalies"][0].symbol == "PLZL@MISX"

print("MARKET_RADAR_FILTERS_OK")
PY
