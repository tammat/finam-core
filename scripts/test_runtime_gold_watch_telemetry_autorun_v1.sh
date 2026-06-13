#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

test -f infra/finam-gold-watch-telemetry.service
test -f infra/finam-gold-watch-telemetry.timer

grep -q "build_runtime_gold_watch_telemetry_v1.py" infra/finam-gold-watch-telemetry.service
grep -q "NoNewPrivileges=true" infra/finam-gold-watch-telemetry.service
grep -q "Europe/Moscow" infra/finam-gold-watch-telemetry.timer
grep -q "10:00/5:00" infra/finam-gold-watch-telemetry.timer

if grep -Eiq "send_order|place_order|create_order|execution_enabled=true|runtime_allowed=true" infra/finam-gold-watch-telemetry.service
then
  echo "GOLD_WATCH_TELEMETRY_AUTORUN_SAFETY_FAIL"
  exit 1
fi

echo TEST_RUNTIME_GOLD_WATCH_TELEMETRY_AUTORUN_V1_OK
