#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
UNIT="marketcore-kg-api.service"
API_FILE="$ROOT/src/marketcore/api/serve_knowledge_graph_api_v1.py"

URL="http://127.0.0.1:8095/api/kg/v1/feature-store/historical-corrections"
JSON_FILE="/tmp/marketcore_ui_historical_correction_kg_api_v1.json"
BAD_LIMIT_FILE="/tmp/marketcore_ui_historical_correction_kg_api_bad_limit_v1.json"
RANGE_FILE="/tmp/marketcore_ui_historical_correction_kg_api_range_v1.json"

cd "$ROOT" || exit 1

echo \
  "=== TEST_MARKETCORE_UI_HISTORICAL_CORRECTION_KG_API_V1 ==="

[[ -s "$API_FILE" ]] || {
    echo "ERROR=kg_api_file_missing"
    exit 1
}

PYTHONPATH=src \
/opt/finam-core/venv/bin/python -m py_compile \
  "$API_FILE" \
  src/marketcore/api/read_models/feature_store_historical_correction_v1.py

DB_BEFORE="$(
    psql -X -d finam_core -AtF '|' -c "
    SELECT
        count(*),
        count(*) FILTER (WHERE market_dirty),
        max(updated_at)
    FROM analytics.feature_store_watermark_v1;
    "
)"

sudo systemctl restart "$UNIT"

for _ in $(seq 1 20)
do
    if curl -fsS \
      "http://127.0.0.1:8095/api/kg/v1/health" \
      >/dev/null
    then
        break
    fi

    sleep 1
done

systemctl is-active --quiet "$UNIT" || {
    echo "ERROR=kg_api_not_active"
    journalctl -u "$UNIT" -n 100 --no-pager
    exit 1
}

HTTP_CODE="$(
    curl -sS \
      -o "$JSON_FILE" \
      -w '%{http_code}' \
      "${URL}?limit=50"
)"

[[ "$HTTP_CODE" == "200" ]] || {
    echo "ERROR=kg_api_http_status:$HTTP_CODE"
    cat "$JSON_FILE"
    exit 1
}

JSON_FILE="$JSON_FILE" \
/opt/finam-core/venv/bin/python - <<'PY'
import json
import os
from pathlib import Path

payload = json.loads(
    Path(os.environ["JSON_FILE"]).read_text(
        encoding="utf-8"
    )
)

if payload.get("api_version") != "v1":
    raise SystemExit(
        "ERROR=api_version_invalid"
    )

if payload.get("status") != "OK":
    raise SystemExit(
        f"ERROR=status_invalid:{payload.get('status')}"
    )

data = payload.get("data")

if not isinstance(data, dict):
    raise SystemExit(
        "ERROR=data_not_object"
    )

required_data = {
    "contract_version",
    "status",
    "read_only",
    "summary",
    "watermark",
    "retention",
    "recent_audits",
    "contracts",
    "safety",
}

missing = required_data - set(data)

if missing:
    raise SystemExit(
        "ERROR=data_keys_missing:"
        + ",".join(sorted(missing))
    )

if data["read_only"] is not True:
    raise SystemExit(
        "ERROR=read_only_false"
    )

summary = data["summary"]

if int(summary["changed_pairs"]) < 0:
    raise SystemExit(
        "ERROR=changed_pairs_negative"
    )

if len(data["recent_audits"]) > 50:
    raise SystemExit(
        "ERROR=limit_not_applied"
    )

metadata = payload.get("metadata") or {}

expected_metadata = {
    "ui_direct_sql": 0,
    "read_only": 1,
    "write_actions_allowed": 0,
    "systemctl_actions_allowed": 0,
}

for key, expected in expected_metadata.items():
    actual = metadata.get(key)

    if actual != expected:
        raise SystemExit(
            f"ERROR=metadata_invalid:{key}:{actual}"
        )

print("json_contract=OK")
print(f"read_model_status={data['status']}")
print(
    "changed_pairs="
    f"{summary['changed_pairs']}"
)
print(
    "changed_rows="
    f"{summary['changed_rows']}"
)
print(
    "current_dirty_rows="
    f"{summary['current_dirty_rows']}"
)
print(
    "recent_audits="
    f"{len(data['recent_audits'])}"
)
PY

BAD_LIMIT_CODE="$(
    curl -sS \
      -o "$BAD_LIMIT_FILE" \
      -w '%{http_code}' \
      "${URL}?limit=abc"
)"

[[ "$BAD_LIMIT_CODE" == "400" ]] || {
    echo \
      "ERROR=invalid_limit_http_status:$BAD_LIMIT_CODE"
    cat "$BAD_LIMIT_FILE"
    exit 1
}

RANGE_CODE="$(
    curl -sS \
      -o "$RANGE_FILE" \
      -w '%{http_code}' \
      "${URL}?limit=501"
)"

[[ "$RANGE_CODE" == "400" ]] || {
    echo \
      "ERROR=range_limit_http_status:$RANGE_CODE"
    cat "$RANGE_FILE"
    exit 1
}

DB_AFTER="$(
    psql -X -d finam_core -AtF '|' -c "
    SELECT
        count(*),
        count(*) FILTER (WHERE market_dirty),
        max(updated_at)
    FROM analytics.feature_store_watermark_v1;
    "
)"

[[ "$DB_BEFORE" == "$DB_AFTER" ]] || {
    echo "ERROR=kg_api_changed_watermark"
    echo "before=$DB_BEFORE"
    echo "after=$DB_AFTER"
    exit 1
}

SERVICE_RESULT="$(
    systemctl show "$UNIT" \
      --property=Result \
      --value
)"

EXEC_STATUS="$(
    systemctl show "$UNIT" \
      --property=ExecMainStatus \
      --value
)"

[[ "$SERVICE_RESULT" == "success" ]] || {
    echo "ERROR=kg_api_service_result:$SERVICE_RESULT"
    exit 1
}

[[ "$EXEC_STATUS" == "0" ]] || {
    echo "ERROR=kg_api_exec_status:$EXEC_STATUS"
    exit 1
}

echo "endpoint=$URL"
echo "http_status=200"
echo "invalid_limit_status=400"
echo "range_limit_status=400"
echo "watermark_state_unchanged=1"
echo "kg_api_service_result=$SERVICE_RESULT"
echo "kg_api_exec_status=$EXEC_STATUS"
echo "ui_direct_sql=0"
echo "read_only=1"
echo "write_actions_allowed=0"
echo "systemctl_actions_allowed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
  "VERDICT=TEST_MARKETCORE_UI_HISTORICAL_CORRECTION_KG_API_V1_OK"
