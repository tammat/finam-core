#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_RU_NORMALIZATION_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore_os/workspace/research.py \
  src/marketcore_os/workspace/edge.py \
  src/marketcore_os/workspace/program.py \
  src/marketcore_os/workspace/portfolio.py \
  src/marketcore_os/workspace/intraday.py \
  src/marketcore_os/workspace/capital_manager.py \
  src/marketcore_os/app.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python <<'PY'
from fastapi.testclient import TestClient
from marketcore_os.app import app

client = TestClient(app)

checks = {
    "/research": ["Исследования", "Статистика", "Следующее действие"],
    "/edge": ["Центр Edge", "Обнаружение", "Проверка", "Реальная торговля"],
    "/program": ["Программа", "Дорожная карта", "Валидация", "Следующий этап"],
    "/portfolio": ["Портфель", "Капитал", "Позиции", "Следующее действие"],
    "/intraday": ["Интрадей", "Активность", "Следующий этап"],
    "/capital-manager": ["Управление капиталом", "Капитал", "Контроль риска", "Следующее действие"],
}

for path, tokens in checks.items():
    r = client.get(path)
    assert r.status_code == 200, path
    html = r.text
    for token in tokens:
        assert token in html, f"{path}: {token}"

print("ru_pages_ready=READY")
PY

echo "VERDICT=MARKETCORE_UI_RU_NORMALIZATION_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_RU_NORMALIZATION_V1_OK"
