#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST NGQ6 PAPER CLUSTER BLOCK ADVISORY V1 ==="
echo "mode=apply_systemd_env_and_diagnostic"
echo "runtime_allow=0"
echo "execution_enabled=0"

python3 -m py_compile src/scripts/research/build_ngq6_paper_cluster_block_advisory_v1.py

sudo mkdir -p /etc/systemd/system/finam-paper-pipeline.service.d

sudo tee /etc/systemd/system/finam-paper-pipeline.service.d/60-ngq6-paper-cluster-advisory.conf >/dev/null <<'EOF'
[Service]
Environment=ENABLE_PAPER_CLUSTER_BLOCK_BYPASS_V1=1
Environment=PAPER_CLUSTER_BLOCK_BYPASS_SYMBOLS=NGN6@RTSX,NGM6@RTSX,NGQ6@RTSX,BRN6@RTSX
EOF

sudo systemctl daemon-reload

systemctl show finam-paper-pipeline.service -p Environment --no-pager | tr ' ' '\n' | \
grep -q "ENABLE_PAPER_CLUSTER_BLOCK_BYPASS_V1=1"

systemctl show finam-paper-pipeline.service -p Environment --no-pager | tr ' ' '\n' | \
grep -q "PAPER_CLUSTER_BLOCK_BYPASS_SYMBOLS=.*NGQ6@RTSX"

bash scripts/test_ngq6_runtime_universe_seed_v1.sh

sudo systemctl restart finam-paper-pipeline.service

sleep 30

python3 src/scripts/research/build_ngq6_paper_cluster_block_advisory_v1.py \
  | tee /tmp/ngq6_paper_cluster_block_advisory_v1.log

grep -q "NGQ6_PAPER_CLUSTER_BLOCK_ADVISORY_V1_OK" /tmp/ngq6_paper_cluster_block_advisory_v1.log
grep -q "ENV_BYPASS_ENABLED=1" /tmp/ngq6_paper_cluster_block_advisory_v1.log
grep -q "ENV_NGQ6_ALLOWED=1" /tmp/ngq6_paper_cluster_block_advisory_v1.log

echo TEST_NGQ6_PAPER_CLUSTER_BLOCK_ADVISORY_V1_OK
