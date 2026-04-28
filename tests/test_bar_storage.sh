#!/bin/bash

echo "Running bar storage test..."

python3 scripts/load_bars.py

RESULT=$?

if [ $RESULT -ne 0 ]; then
  echo "FAILED: script execution error"
  exit 1
fi

COUNT=$(psql -U postgres -d finam -t -c "SELECT COUNT(*) FROM market_bars WHERE symbol='GAZP';")

echo "Rows in DB: $COUNT"

if [ "$COUNT" -gt 0 ]; then
  echo "SUCCESS: bars inserted"
  exit 0
else
  echo "FAILED: no data inserted"
  exit 1
fi