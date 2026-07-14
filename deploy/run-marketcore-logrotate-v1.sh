#!/bin/bash
set -euo pipefail

cd /opt/finam-core
mkdir -p data/logrotate

exec /usr/sbin/logrotate \
  --state data/logrotate/marketcore-runtime.status \
  deploy/logrotate/marketcore-runtime
