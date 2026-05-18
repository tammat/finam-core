#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_replay_campaign.py

python src/scripts/run_replay_campaign.py --help >/dev/null

python src/scripts/run_replay_campaign.py \
  --symbols BRM6@RTSX \
  --timeframes M5 \
  --strategies BR_CONSERVATIVE_BREAKOUT \
  --campaign-id test-campaign \
  --dry-run >/tmp/replay_campaign_test.log

grep -q "REPLAY_CAMPAIGN_START" /tmp/replay_campaign_test.log
grep -q "REPLAY_CAMPAIGN_RUN" /tmp/replay_campaign_test.log
grep -q "REPLAY_CAMPAIGN_DONE" /tmp/replay_campaign_test.log

echo "OK: run_replay_campaign compile"
