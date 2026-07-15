#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=src

venv/bin/python - <<'PY'
from pathlib import Path
for name in (
    "src/scripts/register_marketcore_stage6_ru_catalog_v2.py",
    "src/scripts/audit_marketcore_stage6_i18n_v2.py",
):
    compile(Path(name).read_text(), name, "exec")
PY

venv/bin/python src/scripts/register_marketcore_stage6_ru_catalog_v2.py
venv/bin/python src/scripts/audit_marketcore_stage6_i18n_v2.py --enforce

catalog="$(curl -fsS 'http://127.0.0.1:8080/api/v2/i18n/catalog?locale=ru-RU')"
render_tree="$(curl -fsS 'http://127.0.0.1:8080/api/v2/domain-render-tree/research')"
venv/bin/python - "$catalog" "$render_tree" <<'PY'
import json
import sys

catalog = json.loads(sys.argv[1])
document = json.loads(sys.argv[2])
assert catalog["locale_code"] == "ru-RU"
assert catalog["fallback_locale_code"] == "ru-RU"
assert catalog["messages"]["research.action.request_refresh"] == "Обновить исследовательские данные"
assert catalog["messages"]["research.metric.oos_pass"] == "Прошли вневыборочную проверку"
assert document["locale_code"] == "ru-RU"
assert document["fallback_locale_code"] == "ru-RU"
PY

echo "missing_message_keys=0"
echo "missing_state_translations=0"
echo "message_argument_errors=0"
echo "forbidden_operator_terms=0"
echo "forbidden_semantic_hardcodes=0"
echo "VERDICT=MARKETCORE_STAGE6_COMPLETE_I18N_EXIT_GATE_PASS"
