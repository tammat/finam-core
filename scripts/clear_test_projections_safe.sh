#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

: "${DATABASE_URL:?DATABASE_URL is required}"

if [ "${CONFIRM_CLEAR_TEST_PROJECTIONS:-0}" != "1" ]; then
  echo "REFUSED: set CONFIRM_CLEAR_TEST_PROJECTIONS=1"
  exit 2
fi

psql "$DATABASE_URL" -P pager=off <<'SQL'
SELECT 'position_projection' AS table_name, COUNT(*) FROM position_projection
UNION ALL
SELECT 'order_projection', COUNT(*) FROM order_projection
UNION ALL
SELECT 'event_dead_letters', COUNT(*) FROM event_dead_letters;

TRUNCATE TABLE position_projection CASCADE;
TRUNCATE TABLE order_projection CASCADE;
TRUNCATE TABLE event_dead_letters CASCADE;

SELECT 'CLEARED_TEST_PROJECTIONS_OK' AS result;
SQL
