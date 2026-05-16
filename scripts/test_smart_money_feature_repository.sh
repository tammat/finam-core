#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/create_smart_money_feature_events.sql >/dev/null

python -m py_compile \
  src/finam_core/orderflow/smart_money_features.py \
  src/finam_core/orderflow/smart_money_feature_repository.py

python - <<'PY'
from finam_core.orderflow.smart_money_features import SmartMoneyFeatureLayer
from finam_core.orderflow.smart_money_feature_repository import SmartMoneyFeatureRepository
from finam_core.storage.postgres_logger import PostgresLogger

layer = SmartMoneyFeatureLayer(window=5)

features = layer.update(
    symbol="SBER@MISX",
    price=300.1,
    volume=6000,
    high=300.3,
    low=299.9,
    avg_volume=1000,
)

repo = SmartMoneyFeatureRepository(PostgresLogger())
repo.save(features)

assert features.smart_money_score >= 0
assert features.label in {
    "NORMAL_FLOW",
    "SMART_MONEY_CANDIDATE",
    "INSTITUTIONAL_GRADE",
}

print("OK: smart money feature repository")
PY

psql "$DATABASE_URL" -P pager=off -c "
select symbol, smart_money_score, label
from smart_money_feature_events
where symbol='SBER@MISX'
order by ts desc
limit 1;
"
