#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== NGQ6 CLUSTER ADVISORY ENV FIX V1 ==="
echo "mode=runtime_env_fix_check"
echo "runtime_allow=0"
echo "execution_enabled=0"

echo
echo "=== 1. SYSTEMD DROPINS ==="
systemctl cat finam-paper-pipeline.service | \
grep -E "ENABLE_PAPER_CLUSTER_BLOCK_BYPASS_V1|PAPER_CLUSTER_BLOCK_BYPASS_SYMBOLS" || true

echo
echo "=== 2. DAEMON RELOAD + RESTART ==="
old_pid="$(systemctl show finam-paper-pipeline.service -p MainPID --value || true)"

sudo systemctl daemon-reload
sudo systemctl restart finam-paper-pipeline.service

sleep 5

new_pid="$(systemctl show finam-paper-pipeline.service -p MainPID --value || true)"

echo "old_pid=${old_pid}"
echo "new_pid=${new_pid}"

if [ -z "${new_pid}" ] || [ "${new_pid}" = "0" ]; then
  echo "FAIL: finam-paper-pipeline.service is not running"
  exit 1
fi

echo
echo "=== 3. SYSTEMD ENV CHECK ==="
systemd_env="$(systemctl show finam-paper-pipeline.service -p Environment --no-pager | tr ' ' '\n')"

echo "${systemd_env}" | grep -q "ENABLE_PAPER_CLUSTER_BLOCK_BYPASS_V1=1"
echo "${systemd_env}" | grep -q "PAPER_CLUSTER_BLOCK_BYPASS_SYMBOLS=.*NGQ6@RTSX"

echo "${systemd_env}" | grep -E "ENABLE_PAPER_CLUSTER_BLOCK_BYPASS_V1|PAPER_CLUSTER_BLOCK_BYPASS_SYMBOLS"

echo
echo "=== 4. ACTIVE PROCESS ENV CHECK ==="
process_env="$(sudo cat "/proc/${new_pid}/environ" | tr '\000' '\n')"

echo "${process_env}" | grep -q "ENABLE_PAPER_CLUSTER_BLOCK_BYPASS_V1=1"
echo "${process_env}" | grep -q "PAPER_CLUSTER_BLOCK_BYPASS_SYMBOLS=.*NGQ6@RTSX"

echo "${process_env}" | grep -E "ENABLE_PAPER_CLUSTER_BLOCK_BYPASS_V1|PAPER_CLUSTER_BLOCK_BYPASS_SYMBOLS"

echo
echo "=== 5. NGQ6 SEED CHECK ==="
bash scripts/test_ngq6_runtime_universe_seed_v1.sh

echo
echo "=== 6. AUDIT CHECK ==="
python3 -m py_compile src/scripts/research/build_ngq6_cluster_advisory_runtime_env_audit_v1.py

python3 src/scripts/research/build_ngq6_cluster_advisory_runtime_env_audit_v1.py \
  | tee /tmp/ngq6_cluster_advisory_runtime_env_audit_v1.log

grep -q "NGQ6_CLUSTER_ADVISORY_RUNTIME_ENV_AUDIT_V1_OK" /tmp/ngq6_cluster_advisory_runtime_env_audit_v1.log
grep -q "SYSTEMD_NGQ6_ALLOWED=1" /tmp/ngq6_cluster_advisory_runtime_env_audit_v1.log
grep -q "PROCESS_NGQ6_ALLOWED=1" /tmp/ngq6_cluster_advisory_runtime_env_audit_v1.log

echo "NGQ6_CLUSTER_ADVISORY_ENV_FIX_V1_OK"
