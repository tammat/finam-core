#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_STATUS_BAR_V1 ==="

PYTHONPATH=src python -m py_compile src/marketcore_os/layouts/base.py

PYTHONPATH=src python - <<'PY'
from marketcore_os.layouts.base import render_shell

html = render_shell(
    content="<section>OK</section>",
    lang="ru",
    tz="Europe/Moscow",
    currency="RUB",
    theme="light",
)

for token in ["ONLINE", "MSK", "RUB", "PostgreSQL ✓", "Build", "Рабочее место"]:
    assert token in html, token

html_en = render_shell(
    content="<section>OK</section>",
    lang="en",
    tz="UTC",
    currency="USD",
    theme="dark",
)

for token in ["UTC", "USD", "Workspace", 'class="mc-dark"']:
    assert token in html_en, token

print("status_bar_ready=READY")
print("timezone_clock_ready=READY")
print("postgres_status_ready=READY")
print("build_label_ready=READY")
PY

echo "VERDICT=MARKETCORE_STATUS_BAR_V1_READY"
echo "VERDICT=TEST_MARKETCORE_STATUS_BAR_V1_OK"
