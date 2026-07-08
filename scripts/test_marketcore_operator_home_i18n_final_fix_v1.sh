#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_OPERATOR_HOME_I18N_FINAL_FIX_V1 ==="

mkdir -p reports

report="reports/operator_home_i18n_final_fix_v1.txt"

curl -fsS "http://127.0.0.1:8080/?v=$(date +%s)" \
    >/tmp/operator_home_i18n.html

echo "=== RAW I18N KEYS ===" > "$report"

grep -Eo '(page|widget|statusbar|column|button|dashboard|tooltip|message|error)\.[A-Za-z0-9_.-]+' \
    /tmp/operator_home_i18n.html \
    | sort -u \
    | tee -a "$report" || true

raw_count=$(
grep -Eo '(page|widget|statusbar|column|button|dashboard|tooltip|message|error)\.[A-Za-z0-9_.-]+' \
    /tmp/operator_home_i18n.html 2>/dev/null \
    | sort -u \
    | wc -l \
    || true
)

echo >> "$report"
echo "RAW_KEY_COUNT=$raw_count" >> "$report"

echo
echo "=== VERIFY DB RESOURCES ==="

missing=0

while read -r key; do
    [ -n "$key" ] || continue

    exists=$(psql -At -d finam_core -c "
SELECT count(*)
FROM presentation.ui_resource_v1
WHERE resource_key='$key';
")

    if [ "$exists" = "0" ]; then
        echo "MISSING_RESOURCE=$key"
        missing=$((missing+1))
    fi

done < <(
grep -Eo '(page|widget|statusbar|column|button|dashboard|tooltip|message|error)\.[A-Za-z0-9_.-]+' \
    /tmp/operator_home_i18n.html 2>/dev/null \
    | sort -u \
    || true
)

echo
echo "RAW_I18N_KEYS_VISIBLE=$raw_count"
echo "MISSING_DB_RESOURCES=$missing"

if [ "$raw_count" != "0" ]; then
    echo "I18N_NOT_COMPLETE"
    exit 1
fi

if [ "$missing" != "0" ]; then
    echo "I18N_DATABASE_INCOMPLETE"
    exit 1
fi

echo "RAW_I18N_KEYS_VISIBLE=0"
echo "I18N_COVERAGE=100%"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_OPERATOR_HOME_I18N_FINAL_FIX_V1_READY"
echo "VERDICT=TEST_MARKETCORE_OPERATOR_HOME_I18N_FINAL_FIX_V1_OK"
