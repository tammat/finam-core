#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"
export DATABASE_URL

psql "$DATABASE_URL" -f scripts/alter_position_intents_trade_role.sql

PYTHONPATH=src python scripts/manage_position_intents.py set \
  --symbol TESTROLE@MISX \
  --horizon swing \
  --role reduce_only \
  --comment "test reduce only"

PYTHONPATH=src python scripts/manage_position_intents.py list | grep "TESTROLE@MISX" | grep "reduce_only"

echo "POSITION_INTENT_TRADE_ROLE_OK"
