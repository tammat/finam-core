#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

test -f infra/finam-gold-shadow-validation.service
test -f infra/finam-gold-shadow-validation.timer

grep -q "GOLD_SYMBOL=GDU6@RTSX" infra/finam-gold-shadow-validation.service
grep -q "build_runtime_shadow_validation_gold_v1.py" infra/finam-gold-shadow-validation.service
grep -q "15..18" infra/finam-gold-shadow-validation.timer
grep -q "NoNewPrivileges=true" infra/finam-gold-shadow-validation.service

if grep -Eiq "order|execution|runtime_allow=1|execution_enabled=1" infra/finam-gold-shadow-validation.service
then
  echo "AUTORUN_SAFETY_FAIL"
  exit 1
fi

echo TEST_RUNTIME_SHADOW_VALIDATION_GOLD_AUTORUN_V1_OK
