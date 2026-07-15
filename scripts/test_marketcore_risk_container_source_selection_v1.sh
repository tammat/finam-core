#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
PYTHONPATH=src .venv/bin/python - <<'PY'
import psycopg2

requirements = {
    "public.portfolio_risk_state": {"total_heat", "portfolio_share", "risk_state", "calculated_at"},
    "marketcore_ui.risk_summary_v1": {"runtime_allowed", "execution_allowed", "daily_risk_pct", "refreshed_at"},
    "analytics.risk_decision_snapshot_v1": {"risk_score", "position_risk_score", "exposure_risk_score", "daily_loss_risk_score", "correlation_risk_score", "refreshed_at"},
}
with psycopg2.connect("postgresql:///finam_core") as connection:
    with connection.cursor() as cursor:
        for source, required in requirements.items():
            schema, table = source.split(".")
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s", (schema, table))
            columns = {row[0] for row in cursor.fetchall()}
            assert required <= columns, (source, sorted(required - columns))
            cursor.execute(f"SELECT count(*) FROM {source}")
            assert cursor.fetchone()[0] > 0, source
print("risk_owned_sources=3")
print("portfolio_drawdown_source=UNAVAILABLE")
print("freshness_required=1")
print("VERDICT=MARKETCORE_RISK_CONTAINER_SOURCES_SELECTED")
PY
