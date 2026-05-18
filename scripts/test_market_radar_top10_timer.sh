#!/usr/bin/env bash
set -euo pipefail

test -f systemd/market-radar-top10.service
test -f systemd/market-radar-top10.timer

grep -q "run_market_radar.py" systemd/market-radar-top10.service
grep -q -- "--telegram-top5" systemd/market-radar-top10.service
grep -q "OnUnitActiveSec=15min" systemd/market-radar-top10.timer

echo "OK: market radar top10 timer"
