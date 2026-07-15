#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
PYTHONPATH=src .venv/bin/python -m py_compile src/marketcore/presentation/i18n/catalog_http_v2.py src/marketcore/presentation/router.py src/marketcore/presentation/app.py
PYTHONPATH=src .venv/bin/python - <<'PY'
import json
from marketcore.presentation.i18n.catalog_http_v2 import i18n_catalog_http_v2
from marketcore.presentation.router import route

response = i18n_catalog_http_v2("ru-RU")
assert response.status_code == 200
payload = json.loads(response.body)
assert payload["schema_version"] == "marketcore.i18n_catalog.v2"
assert payload["locale_code"] == "ru-RU"
assert len(payload["messages"]) >= 600
assert payload["messages"]["button.open"] == "Открыть"
status, body = route("/api/v2/i18n/catalog", {"locale": ["ru-RU"]})
assert status == 200 and json.loads(body)["messages"]["button.open"] == "Открыть"
print(f'messages={len(payload["messages"])}')
PY
curl -fsS -D /tmp/marketcore-i18n-v2.headers -o /tmp/marketcore-i18n-v2.json 'http://127.0.0.1:8080/api/v2/i18n/catalog?locale=ru-RU'
grep -qi '^Content-Type: application/vnd.marketcore.i18n-catalog+json; charset=utf-8' /tmp/marketcore-i18n-v2.headers
grep -q '"schema_version":"marketcore.i18n_catalog.v2"' /tmp/marketcore-i18n-v2.json
echo MARKETCORE_I18N_CATALOG_HTTP_V2_OK
