#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

grep -q "FINAM_ENV_FILE" src/finam_core/notifications/telegram_notifier.py
grep -q "deploy/env/.env" src/finam_core/notifications/telegram_notifier.py
grep -q "override=False" src/finam_core/notifications/telegram_notifier.py
! grep -q '"/opt/finam-core/.env"' src/finam_core/notifications/telegram_notifier.py

python -m py_compile src/finam_core/notifications/telegram_notifier.py
python -m py_compile src/scripts/run_market_pipeline.py

echo "TELEGRAM_NOTIFIER_ENV_FILE_TEST_OK"
