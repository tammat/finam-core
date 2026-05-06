#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"
export DATABASE_URL

psql "$DATABASE_URL" -f scripts/create_position_intents.sql

PYTHONPATH=src python scripts/manage_position_intents.py set \
  --symbol BRM6@RTSX \
  --horizon intraday \
  --comment "test intraday"

PYTHONPATH=src python scripts/manage_position_intents.py set \
  --symbol BRM6@RTSX \
  --horizon swing \
  --comment "test move to swing"

PYTHONPATH=src python scripts/manage_position_intents.py list | grep "BRM6@RTSX"

echo "POSITION_INTENT_DB_OK"
