#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -d finam_core <<'SQL'
CREATE TABLE IF NOT EXISTS runtime_alert_dedup (
    alert_key TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_sent_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);
SQL

echo "OK: runtime_alert_dedup created"
