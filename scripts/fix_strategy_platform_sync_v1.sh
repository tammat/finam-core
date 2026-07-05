#!/usr/bin/env bash
set -euo pipefail

echo "=== FIX_STRATEGY_PLATFORM_SYNC_V1 ==="

python - <<'PY'
from pathlib import Path

p = Path("src/scripts/build_strategy_platform_sync_v1.py")
s = p.read_text(encoding="utf-8")

s = s.replace(
'''    keys = {k: v for k, v in keys.items() if k in cols}

    where = " AND ".join([f"{k}=%s" for k in keys])
''',
'''    keys = {k: v for k, v in keys.items() if k in cols}

    if not keys:
        raise RuntimeError(f"UPSERT_KEYS_EMPTY table={table} available_columns={sorted(cols)}")

    where = " AND ".join([f"{k}=%s" for k in keys])
'''
)

s = s.replace(
'''                for feature in feature_map.get(r["category"], ["feature_quality_score"]):
                    upsert_by_keys(
                        cur,
                        "analytics.strategy_dependency_v1",
                        {
                            "strategy_family": family,
                            "strategy_version": version,
                            "feature_name": feature,
                        },
                        {
                            "required": True,
                            "weight": 1.0,
                            "source_version": "STRATEGY_PLATFORM_SYNC_V1",
                        },
                    )
                    deps += 1
''',
'''                dep_cols = table_columns(cur, "analytics.strategy_dependency_v1")
                for feature in feature_map.get(r["category"], ["feature_quality_score"]):
                    if {"strategy_family", "strategy_version", "feature_name"}.issubset(dep_cols):
                        dep_keys = {
                            "strategy_family": family,
                            "strategy_version": version,
                            "feature_name": feature,
                        }
                    elif {"strategy_family", "feature_name"}.issubset(dep_cols):
                        dep_keys = {
                            "strategy_family": family,
                            "feature_name": feature,
                        }
                    elif {"strategy_name", "feature_name"}.issubset(dep_cols):
                        dep_keys = {
                            "strategy_name": r["strategy_code"],
                            "feature_name": feature,
                        }
                    else:
                        print(f"SKIP_DEPENDENCY_UNSUPPORTED_COLUMNS columns={sorted(dep_cols)}")
                        continue

                    upsert_by_keys(
                        cur,
                        "analytics.strategy_dependency_v1",
                        dep_keys,
                        {
                            "strategy_family": family,
                            "strategy_version": version,
                            "strategy_name": r["strategy_code"],
                            "feature_name": feature,
                            "required": True,
                            "weight": 1.0,
                            "source_version": "STRATEGY_PLATFORM_SYNC_V1",
                        },
                    )
                    deps += 1
'''
)

p.write_text(s, encoding="utf-8")
PY

PYTHONPATH=src python -m py_compile src/scripts/build_strategy_platform_sync_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_strategy_platform_sync_v1.py | tee /tmp/strategy_platform_sync_fix_v1.txt

grep -q "VERDICT=STRATEGY_PLATFORM_SYNC_V1_READY" /tmp/strategy_platform_sync_fix_v1.txt

registry_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.strategy_registry_v1;")
library_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.strategy_library_v1 WHERE enabled=true;")

test "$registry_rows" -ge "$library_rows"

echo "registry_rows=$registry_rows"
echo "library_rows=$library_rows"
echo "VERDICT=FIX_STRATEGY_PLATFORM_SYNC_V1_OK"
