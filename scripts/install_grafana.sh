#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core/ops/grafana

sudo docker compose up -d

echo "GRAFANA_INSTALLED"
echo "URL: http://localhost:3000"
echo "USER: admin"
echo "PASSWORD: finam_admin"
