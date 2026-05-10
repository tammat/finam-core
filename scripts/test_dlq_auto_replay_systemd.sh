#!/usr/bin/env bash
set -euo pipefail

test -f systemd/finam-dlq-auto-replay.service
test -f systemd/finam-dlq-auto-replay.timer

grep -q "Finam Core DLQ Auto Replay Worker" systemd/finam-dlq-auto-replay.service
grep -q "Type=oneshot" systemd/finam-dlq-auto-replay.service
grep -q "python -m finam_core.events.dead_letter_auto_replay_worker" systemd/finam-dlq-auto-replay.service

grep -q "OnBootSec=60" systemd/finam-dlq-auto-replay.timer
grep -q "OnUnitActiveSec=300" systemd/finam-dlq-auto-replay.timer
grep -q "timers.target" systemd/finam-dlq-auto-replay.timer

test -x scripts/install_dlq_auto_replay_systemd.sh

echo "DLQ_AUTO_REPLAY_SYSTEMD_OK"
