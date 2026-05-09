#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.storage.daily_risk_repository import DailyRiskRepository

class Cur:
    def execute(self, sql):
        assert "portfolio_snapshots" in sql
    def fetchall(self):
        return [{"equity": 100000}, {"equity": 99000}, {"equity": 97000}]
    def __enter__(self): return self
    def __exit__(self, *args): return False

class Conn:
    def cursor(self, *args, **kwargs): return Cur()
    def __enter__(self): return self
    def __exit__(self, *args): return False

repo = DailyRiskRepository(database_url="fake")
repo._connect = lambda: Conn()

assert repo.load_today_equities() == [100000.0, 99000.0, 97000.0]

print("DAILY_RISK_REPOSITORY_OK")
PY
