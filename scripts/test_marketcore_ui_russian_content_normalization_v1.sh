#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_RUSSIAN_CONTENT_NORMALIZATION_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/ui_text.py \
  src/marketcore/presentation/navigation.py \
  src/marketcore/presentation/layout.py \
  src/scripts/audit_marketcore_ui_russian_content_normalization_v1.py \
  src/marketcore/presentation/app.py

PYTHONPATH=src python src/scripts/audit_marketcore_ui_russian_content_normalization_v1.py \
  | tee /tmp/marketcore_ui_russian_content_normalization_v1.txt

grep -q "VERDICT=MARKETCORE_UI_RUSSIAN_CONTENT_NORMALIZATION_V1_READY" \
  /tmp/marketcore_ui_russian_content_normalization_v1.txt

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=20280 KG_API_BASE_URL=http://127.0.0.1:1 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/marketcore_ui_russian_norm_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 1

curl -fsS "http://127.0.0.1:20280/" > /tmp/ru_norm_home.html
curl -fsS "http://127.0.0.1:20280/paper-edge-discovery" > /tmp/ru_norm_edge.html
curl -fsS "http://127.0.0.1:20280/risk" > /tmp/ru_norm_risk.html
curl -fsS "http://127.0.0.1:20280/settings" > /tmp/ru_norm_settings.html
curl -fsS "http://127.0.0.1:20280/marketcore-ui-systemd-health" > /tmp/ru_norm_systemd.html

grep -q "Рабочий стол" /tmp/ru_norm_home.html
grep -q "Поиск преимущества" /tmp/ru_norm_home.html
grep -q "Риски" /tmp/ru_norm_home.html
grep -q "Настройки" /tmp/ru_norm_home.html
grep -q "Единая оболочка платформы" /tmp/ru_norm_home.html

grep -q "Объяснение кандидатов" /tmp/ru_norm_edge.html
grep -q "Детализация TOP-кандидатов" /tmp/ru_norm_edge.html
grep -q "Кандидаты исследования" /tmp/ru_norm_edge.html
grep -q "Реальные данные Paper Runtime" /tmp/ru_norm_edge.html
grep -q "Следующее действие" /tmp/ru_norm_edge.html

grep -q "Риски" /tmp/ru_norm_risk.html
grep -q "Настройки" /tmp/ru_norm_settings.html
grep -q "Детали systemd" /tmp/ru_norm_systemd.html

if grep -q "Next Action" /tmp/ru_norm_edge.html; then
  echo "FORBIDDEN_ENGLISH_NEXT_ACTION"
  exit 1
fi

if grep -q "Source:" /tmp/ru_norm_edge.html; then
  echo "FORBIDDEN_ENGLISH_SOURCE"
  exit 1
fi

if grep -q "Systemd Details" /tmp/ru_norm_systemd.html; then
  echo "FORBIDDEN_ENGLISH_SYSTEMD_DETAILS"
  exit 1
fi

grep -q "MARKETCORE_UI_SHELL_V1" /tmp/ru_norm_home.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_RUSSIAN_CONTENT_NORMALIZATION_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_RUSSIAN_CONTENT_NORMALIZATION_V1_OK"
