#!/usr/bin/env bash
set -euo pipefail

export DATABASE_URL="${DATABASE_URL:-dbname=finam user=alex host=localhost}"

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
