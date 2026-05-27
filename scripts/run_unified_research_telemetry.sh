#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m finam_core.research.unified_research_telemetry \
  --strategy "${STRATEGY:-br_conservative_breakout}" \
  --symbol "${SYMBOL:-BRN6@RTSX}"
