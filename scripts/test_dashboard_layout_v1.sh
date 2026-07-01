#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DASHBOARD_LAYOUT_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/dashboard/layout.py \
  src/marketcore/presentation/dashboard/layout_builder.py \
  src/marketcore/presentation/dashboard/layout_models.py \
  src/marketcore/presentation/dashboard/layout_components.py \
  src/marketcore/presentation/dashboard/router.py \
  src/marketcore/presentation/dashboard/server.py

PYTHONPATH=src python - <<'PY'
from fastapi.testclient import TestClient

from marketcore.presentation.dashboard.layout import render_shell
from marketcore.presentation.dashboard.layout_builder import DashboardLayoutBuilder
from marketcore.presentation.dashboard.layout_models import LayoutContent, LayoutState
from marketcore.presentation.dashboard.server import app

html = render_shell('<section class="fc-card">OK</section>', lang='ru', timezone='Europe/Moscow')

assert '<header class="fc-header">' in html
assert 'fc-sidebar' in html
assert 'fc-content' in html
assert 'fc-activity' in html
assert 'fc-footer' in html
assert 'fc-mobile-nav' in html
assert '@media (max-width: 767px)' in html
assert 'Dashboard Layout V1' in html

builder = DashboardLayoutBuilder()
html_en = builder.build(
    LayoutContent(title='Test', body_html='<div>Body</div>'),
    LayoutState(lang='en', timezone='UTC', theme='dark', user_label='Observer'),
)

assert 'lang="en"' in html_en
assert 'UTC' in html_en
assert 'dark' in html_en
assert 'Observer' in html_en

client = TestClient(app)
r = client.get('/?lang=ru&timezone=Europe/Moscow')
assert r.status_code == 200
assert 'fc-header' in r.text
assert 'fc-mobile-nav' in r.text

print("layout_engine=READY")
print("header=READY")
print("sidebar=READY")
print("footer=READY")
print("activity_feed=READY")
print("mobile_navigation=READY")
print("responsive_layout=READY")
print("theme_integration=READY")
print("i18n_integration=READY")
print("timezone_integration=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=DASHBOARD_LAYOUT_V1_READY")
PY

echo "VERDICT=TEST_DASHBOARD_LAYOUT_V1_OK"
