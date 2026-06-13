#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

test -f infra/finam-gold-stability-monitor.service
test -f infra/finam-gold-stability-monitor.timer

grep -q "build_gold_shadow_stability_monitor_v1.py" infra/finam-gold-stability-monitor.service
grep -q "NoNewPrivileges=true" infra/finam-gold-stability-monitor.service
grep -q "Europe/Moscow" infra/finam-gold-stability-monitor.timer
grep -q "10:00/30:00" infra/finam-gold-stability-monitor.timer

if grep -Eiq "send_order|place_order|create_order|execution_enabled=true|runtime_allowed=true" infra/finam-gold-stability-monitor.service
then
  echo "GOLD_STABILITY_MONITOR_AUTORUN_SAFETY_FAIL"
  exit 1
fi

echo TEST_GOLD_SHADOW_STABILITY_MONITOR_AUTORUN_V1_OK
