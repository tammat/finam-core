#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "TEST_NG_M1_ACTIVE_CONTRACT_OVERRIDE_V1_START"

test -f deploy/systemd/finam-paper-pipeline.service.d/30-ng-active-contract.conf
grep -q "Environment=NG_M1_BREAKOUT_SYMBOL=NGN6@RTSX" \
  deploy/systemd/finam-paper-pipeline.service.d/30-ng-active-contract.conf

echo "TEST_NG_M1_ACTIVE_CONTRACT_OVERRIDE_V1_OK"
