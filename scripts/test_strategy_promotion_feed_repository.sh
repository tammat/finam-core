#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/runtime/strategy_promotion_feed.py \
  src/finam_core/runtime/strategy_promotion_feed_repository.py \
  src/scripts/build_strategy_promotion_feed.py

echo "TEST_STRATEGY_PROMOTION_FEED_REPOSITORY_OK"
