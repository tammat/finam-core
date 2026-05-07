#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
import src.scripts.run_volatility_scan as r

calls = []

class FakeCursor:
    def execute(self, sql, params=None):
        calls.append((sql, params))
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False

class FakeConn:
    def cursor(self, *args, **kwargs):
        return FakeCursor()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False

r.psycopg2.connect = lambda database_url: FakeConn()

result = {
    "intraday": [
        {"symbol": "SBER@MISX", "score": 1.5, "atr_pct": 0.01, "turnover": 1000, "volume": 10, "avg_volume": 8}
    ],
    "swing": [
        {"symbol": "BRM6@RTSX", "score": 2.5, "atr_pct": 0.02, "turnover": 2000, "volume": 20, "avg_volume": 12}
    ],
}

saved = r.save_scan_results("postgresql://fake", "M5", result)

assert saved == 2, saved
assert len(calls) == 2, calls
assert "INSERT INTO volatility_scan_results" in calls[0][0]
assert calls[0][1][0] == "M5"
assert calls[0][1][1] == "intraday"
assert calls[0][1][3] == "SBER@MISX"
assert calls[1][1][1] == "swing"
assert calls[1][1][3] == "BRM6@RTSX"

print("RUN_VOLATILITY_SCAN_SAVE_MOCK_OK")
PY
