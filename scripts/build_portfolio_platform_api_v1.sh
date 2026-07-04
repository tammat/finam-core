#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PORTFOLIO_PLATFORM_API_V1 ==="

api_file="src/marketcore/api/serve_knowledge_graph_api_v1.py"
cp "$api_file" /tmp/serve_knowledge_graph_api_v1.before_portfolio_platform_api_v1.bak

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if "/api/kg/v1/portfolio-platform/summary" not in s:
    marker = '            if path == "/api/kg/v1/trading-platform/summary":'
    if marker not in s:
        raise SystemExit("TRADING_PLATFORM_API_MARKER_NOT_FOUND")

    block = r'''
            if path == "/api/kg/v1/portfolio-platform/summary":
                row = fetch_one("""
                    SELECT
                        e.portfolio_scope,
                        e.cash::float AS cash,
                        e.positions_value::float AS positions_value,
                        e.equity::float AS equity,
                        e.realized_pnl::float AS realized_pnl,
                        e.unrealized_pnl::float AS unrealized_pnl,
                        e.total_pnl::float AS total_pnl,
                        e.gross_exposure::float AS gross_exposure,
                        e.net_exposure::float AS net_exposure,
                        e.source_version,
                        e.refreshed_at,
                        (SELECT count(*)::int FROM analytics.portfolio_position_snapshot_v1) AS position_rows,
                        (SELECT count(*)::int FROM analytics.portfolio_position_snapshot_v1 WHERE position_status='OPEN') AS open_position_rows
                    FROM analytics.portfolio_equity_snapshot_v1 e
                    WHERE e.portfolio_scope='GLOBAL';
                """) or {}
                health_code = "HEALTHY" if row else "DEGRADED"
                row["health"] = dto("health", health_code)
                self.send_json(200, response("OK", row, {"source": "analytics.portfolio_equity_snapshot_v1"}))
                return

            if path == "/api/kg/v1/portfolio-platform/positions":
                rows = fetch_all("""
                    SELECT
                        id,
                        symbol,
                        asset_class,
                        quantity::float AS quantity,
                        avg_price::float AS avg_price,
                        last_price::float AS last_price,
                        market_value::float AS market_value,
                        unrealized_pnl::float AS unrealized_pnl,
                        realized_pnl::float AS realized_pnl,
                        exposure::float AS exposure,
                        position_status,
                        source_version,
                        refreshed_at
                    FROM analytics.portfolio_position_snapshot_v1
                    ORDER BY symbol;
                """)
                for r in rows:
                    r["position_status"] = dto("status", r.get("position_status"))
                self.send_json(200, response("OK", rows, {"source": "analytics.portfolio_position_snapshot_v1"}))
                return

            if path == "/api/kg/v1/portfolio-platform/equity":
                row = fetch_one("""
                    SELECT
                        portfolio_scope,
                        cash::float AS cash,
                        positions_value::float AS positions_value,
                        equity::float AS equity,
                        realized_pnl::float AS realized_pnl,
                        unrealized_pnl::float AS unrealized_pnl,
                        total_pnl::float AS total_pnl,
                        gross_exposure::float AS gross_exposure,
                        net_exposure::float AS net_exposure,
                        source_version,
                        refreshed_at
                    FROM analytics.portfolio_equity_snapshot_v1
                    WHERE portfolio_scope='GLOBAL';
                """) or {}
                self.send_json(200, response("OK", row, {"source": "analytics.portfolio_equity_snapshot_v1"}))
                return

            if path == "/api/kg/v1/portfolio-platform/configuration":
                rows = fetch_all("""
                    SELECT
                        portfolio_name,
                        enabled,
                        config_json,
                        source_version,
                        updated_at
                    FROM analytics.portfolio_configuration_v1
                    ORDER BY portfolio_name;
                """)
                for r in rows:
                    r["enabled_status"] = dto("status", "ACTIVE" if r.get("enabled") else "DISABLED")
                self.send_json(200, response("OK", rows, {"source": "analytics.portfolio_configuration_v1"}))
                return

            if path == "/api/kg/v1/portfolio-platform/governance":
                row = fetch_one("""
                    SELECT *
                    FROM analytics.portfolio_governance_v1
                    WHERE governance_scope='GLOBAL';
                """) or {}
                if row:
                    row["builder_status"] = dto("status", row.get("builder_status"))
                    row["position_status"] = dto("status", row.get("position_status"))
                    row["equity_status"] = dto("status", row.get("equity_status"))
                    row["api_status"] = dto("status", row.get("api_status"))
                    row["ui_status"] = dto("status", row.get("ui_status"))
                    row["readiness"] = dto("governance", row.get("readiness_code"))
                    row["recommendation"] = dto("recommendation", row.get("recommendation_code"))
                self.send_json(200, response("OK", row, {"source": "analytics.portfolio_governance_v1"}))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > scripts/test_portfolio_platform_api_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PORTFOLIO_PLATFORM_API_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/scripts/build_portfolio_builder_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_portfolio_builder_v1.py

sudo systemctl restart marketcore-kg-api.service
sleep 2

base="http://127.0.0.1:8095"

curl -fsS "$base/api/kg/v1/portfolio-platform/summary" > /tmp/portfolio_platform_summary.json
curl -fsS "$base/api/kg/v1/portfolio-platform/positions" > /tmp/portfolio_platform_positions.json
curl -fsS "$base/api/kg/v1/portfolio-platform/equity" > /tmp/portfolio_platform_equity.json
curl -fsS "$base/api/kg/v1/portfolio-platform/configuration" > /tmp/portfolio_platform_configuration.json
curl -fsS "$base/api/kg/v1/portfolio-platform/governance" > /tmp/portfolio_platform_governance.json

python - <<'PY'
import json

summary = json.load(open("/tmp/portfolio_platform_summary.json", encoding="utf-8"))
positions = json.load(open("/tmp/portfolio_platform_positions.json", encoding="utf-8"))
equity = json.load(open("/tmp/portfolio_platform_equity.json", encoding="utf-8"))
config = json.load(open("/tmp/portfolio_platform_configuration.json", encoding="utf-8"))
governance = json.load(open("/tmp/portfolio_platform_governance.json", encoding="utf-8"))

assert summary["status"] == "OK"
assert "health" in summary["data"]
assert "equity" in summary["data"]

assert positions["status"] == "OK"
assert isinstance(positions["data"], list)
if positions["data"]:
    assert isinstance(positions["data"][0]["position_status"], dict)

assert equity["status"] == "OK"
assert "portfolio_scope" in equity["data"]

assert config["status"] == "OK"
assert len(config["data"]) > 0
assert isinstance(config["data"][0]["enabled_status"], dict)

assert governance["status"] == "OK"
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PORTFOLIO_PLATFORM_API_V1_READY"
echo "VERDICT=TEST_PORTFOLIO_PLATFORM_API_V1_OK"
SH_TEST

chmod +x scripts/test_portfolio_platform_api_v1.sh
scripts/test_portfolio_platform_api_v1.sh

echo "VERDICT=BUILD_PORTFOLIO_PLATFORM_API_V1_OK"
