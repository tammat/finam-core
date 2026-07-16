#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src timeout 180 venv/bin/pytest -q \
  tests/test_stage9_home_v2_shell_cutover.py \
  tests/test_control_center_render_tree_v2.py \
  tests/test_home_operator_decision_render_tree_v2.py \
  tests/test_action_http_controller_v2.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src timeout 60 venv/bin/python - <<'PY'
import json
import urllib.error
import urllib.request

shell = urllib.request.urlopen("http://127.0.0.1:8080/", timeout=10).read().decode("utf-8")
assert 'data-marketcore-ui-runtime="v2"' in shell
assert "/ui-runtime/v1/" not in shell
document = json.load(urllib.request.urlopen(
    "http://127.0.0.1:8080/api/v2/domain-render-tree/control-center", timeout=20
))
encoded = json.dumps(document, ensure_ascii=False)
for label in (
    "Исследования", "Кандидаты", "Подтверждённое преимущество",
    "Вневыборочная проверка", "Форвардное наблюдение",
    "Теневое наблюдение", "Бумажная торговля",
    "Допуск к исполнению", "Реальная торговля", "Прибыль",
):
    assert label in encoded, label
for path in (
    "/api/v1/render-tree/home", "/api/v1/render-tree/portfolio",
    "/api/v2/render-tree/control-center/edge",
    "/assets/marketcore/ui-runtime/v1/runtime.js",
):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:8080{path}", timeout=10)
    except urllib.error.HTTPError as error:
        assert error.code == 410, (path, error.code)
        assert b"LEGACY_PRESENTATION_RETIRED" in error.read(), path
    else:
        raise AssertionError(f"legacy path is still live: {path}")
for path in ("/workspace-v2/portfolio", "/workspace-v2/control-center/edge-oos"):
    page = urllib.request.urlopen(f"http://127.0.0.1:8080{path}", timeout=10)
    assert page.status == 200
    assert b'data-marketcore-ui-runtime="v2"' in page.read()
PY

test "$(psql -d finam_core -Atqc "SELECT count(*) FROM public.orders WHERE exchange_order_id IS NOT NULL")" -eq 0
echo "legacy_presentation_callers=0"
echo "canonical_runtime=V2"
echo "real_trading_changed=0"
echo "VERDICT=MARKETCORE_STAGE9_LEGACY_PRESENTATION_EXIT_GATE_PASS"
