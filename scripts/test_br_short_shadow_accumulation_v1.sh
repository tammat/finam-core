#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/governance/br_short_shadow_policy_v1.py \
  src/finam_core/governance/br_short_shadow_accumulator_v1.py \
  src/finam_core/pipelines/paper_pipeline.py

python3 - <<'PY'
import os
import psycopg2

from finam_core.pipelines.paper_pipeline import _br_short_shadow_pipeline_hook_v1

dsn = os.environ["DATABASE_URL"]

ok = _br_short_shadow_pipeline_hook_v1(
    symbol="BRN6@RTSX",
    side="SELL",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    current_position=0.0,
    signal_id="test-br-short-shadow-accumulation-v1",
    price=93.5,
    quantity=1.0,
)

assert ok is True

with psycopg2.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            select count(*)
            from research_br_short_shadow_signals
            where signal_id='test-br-short-shadow-accumulation-v1'
              and symbol='BRN6@RTSX'
              and side='SELL'
              and strategy='BR_CONSERVATIVE_BREAKOUT'
              and shadow_logged=true
              and reason='br_short_shadow_open_short_candidate';
            """
        )
        rows = int(cur.fetchone()[0])
        assert rows >= 1, rows

        cur.execute(
            """
            delete from research_br_short_shadow_signals
            where signal_id='test-br-short-shadow-accumulation-v1';
            """
        )

print("PY_ASSERTIONS_OK")
PY

echo BR_SHORT_SHADOW_ACCUMULATION_V1_OK
