#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.data.volatility_scanner import VolatilityScanner

rows = [
    {
        "symbol": "SVETP@MISX",
        "open": 21.0,
        "high": 24.0,
        "low": 20.8,
        "close": 23.4,
        "last": 23.4,
        "bid": 23.39,
        "ask": 23.41,
        "volume": 3_000_000,
        "avg_volume": 1_000_000,
        "turnover": 600_000_000,
    },
    {
        "symbol": "SBER@MISX",
        "open": 300.0,
        "high": 306.0,
        "low": 299.0,
        "close": 305.0,
        "last": 305.0,
        "bid": 304.99,
        "ask": 305.01,
        "volume": 50_000_000,
        "avg_volume": 40_000_000,
        "turnover": 15_000_000_000,
    },
    {
        "symbol": "BAD@MISX",
        "open": 10.0,
        "high": 10.1,
        "low": 10.0,
        "close": 10.05,
        "last": 10.05,
        "bid": 10.0,
        "ask": 10.2,
        "volume": 10_000,
        "avg_volume": 20_000,
        "turnover": 100_000,
    },
]

scanner = VolatilityScanner(min_turnover=300_000_000, max_spread_pct=0.0025)
result = scanner.scan(rows, top_n=5)

intraday_symbols = [item.symbol for item in result["intraday"]]
swing_symbols = [item.symbol for item in result["swing"]]

assert "SVETP@MISX" in intraday_symbols, result
assert "SBER@MISX" in intraday_symbols, result
assert "BAD@MISX" not in intraday_symbols, result
assert "SVETP@MISX" in swing_symbols, result
assert result["intraday"][0].score >= result["intraday"][-1].score, result
assert result["intraday"][0].reason == "passed", result

print("VOLATILITY_SCANNER_OK")
PY
