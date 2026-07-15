#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/pytest -q tests/test_profit_funnel_source_registry_v2.py
audit="$(PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/python src/scripts/audit_marketcore_profit_funnel_sources_v2.py)"
echo "$audit"
grep -q 'stage=PROFIT .* scope=REAL .* quality=UNAVAILABLE ' <<<"$audit"
grep -q 'stage=LIVE .* scope=SCOPE_UNVERIFIED ' <<<"$audit"
echo "source_registry_read_only=PASS"
echo "unverified_scope_not_promoted=PASS"
echo "VERDICT=MARKETCORE_STAGE7_PROFIT_FUNNEL_SOURCES_V2_READY"
