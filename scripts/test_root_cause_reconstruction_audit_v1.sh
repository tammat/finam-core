#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

bash scripts/root_cause_reconstruction_audit_v1.sh \
  | tee /tmp/root_cause_reconstruction_audit_v1.log

grep -q "ROOT CAUSE RECONSTRUCTION AUDIT V1" \
  /tmp/root_cause_reconstruction_audit_v1.log

grep -q "STEP_1_ATTRIBUTION_CHAIN_COUNTS" \
  /tmp/root_cause_reconstruction_audit_v1.log

grep -q "STEP_7_ROOT_CAUSE_VERDICT" \
  /tmp/root_cause_reconstruction_audit_v1.log

grep -q "ROOT_CAUSE_RECONSTRUCTION_AUDIT_V1_OK" \
  /tmp/root_cause_reconstruction_audit_v1.log

echo TEST_ROOT_CAUSE_RECONSTRUCTION_AUDIT_V1_OK
