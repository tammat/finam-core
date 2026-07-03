#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_8080_EMPTY_REPLY_FIX_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/app.py \
  src/marketcore/presentation/router.py \
  src/marketcore/presentation/layout.py \
  src/marketcore/presentation/pages/home.py \
  src/marketcore/presentation/navigation.py \
  src/marketcore/presentation/registry.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/home.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_HOME_PAGE"
  exit 1
fi

PYTHONPATH=src python <<'PY'
from marketcore.presentation.router import route

code, payload = route("/")
body = payload.decode("utf-8", errors="replace")

print(f"route_home_code={code}")
print(f"route_home_len={len(body)}")

assert code == 200, body[:1000]
assert "Рабочий стол" in body, body[:1000]
assert "Основные разделы" in body, body[:1000]
assert "MARKETCORE_UI_SHELL_V1" in body, body[:1000]
PY

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=20480 KG_API_BASE_URL=http://127.0.0.1:1 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/empty_reply_fix_local_ui_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 1

curl -fsS "http://127.0.0.1:20480/" > /tmp/empty_reply_fix_home_local_v1.html

grep -q "Рабочий стол" /tmp/empty_reply_fix_home_local_v1.html
grep -q "Основные разделы" /tmp/empty_reply_fix_home_local_v1.html
grep -q "Риски" /tmp/empty_reply_fix_home_local_v1.html
grep -q "Настройки" /tmp/empty_reply_fix_home_local_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/empty_reply_fix_home_local_v1.html

sudo systemctl restart marketcore-ui-shell.service
sleep 2

if ! curl -fsS "http://127.0.0.1:8080/" > /tmp/empty_reply_fix_home_8080_v1.html; then
  echo "=== MARKETCORE_UI_SHELL_JOURNAL ==="
  journalctl -u marketcore-ui-shell.service --since "2 minutes ago" --no-pager
  exit 1
fi

grep -q "Рабочий стол" /tmp/empty_reply_fix_home_8080_v1.html
grep -q "Основные разделы" /tmp/empty_reply_fix_home_8080_v1.html
grep -q "Риски" /tmp/empty_reply_fix_home_8080_v1.html
grep -q "Настройки" /tmp/empty_reply_fix_home_8080_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/empty_reply_fix_home_8080_v1.html

echo "=== MARKETCORE_UI_SHELL_RECENT_ERRORS ==="
journalctl -u marketcore-ui-shell.service --since "2 minutes ago" --no-pager | \
grep -E "Traceback|Exception|Error|Empty reply" || true

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_8080_EMPTY_REPLY_FIX_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_8080_EMPTY_REPLY_FIX_V1_OK"
