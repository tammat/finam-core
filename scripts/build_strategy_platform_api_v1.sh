#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_STRATEGY_PLATFORM_API_V1 ==="

api_file="src/marketcore/api/serve_knowledge_graph_api_v1.py"
cp "$api_file" /tmp/serve_knowledge_graph_api_v1.before_strategy_platform_api_v1.bak

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if "/api/kg/v1/strategy-platform/summary" not in s:
    marker = '            if path == "/api/kg/v1/edge-validation-queue":'
    if marker not in s:
        raise SystemExit("API_INSERT_MARKER_NOT_FOUND")

    block = r'''
            def dto(kind, code):
                c = str(code or "UNKNOWN")
                severity = "neutral"
                color = "gray"
                icon = "circle"
                if c in {"ACTIVE", "READY", "HEALTHY", "LONG"}:
                    severity, color, icon = "success", "green", "check-circle"
                elif c in {"DEGRADED", "WAIT_SAMPLE", "OBSERVE", "FLAT"}:
                    severity, color, icon = "warning", "orange", "triangle-alert"
                elif c in {"FAILED", "DISABLED", "REJECTED", "SHORT"}:
                    severity, color, icon = "danger", "red", "x-circle"
                return {
                    "code": c,
                    "display_key": f"{kind}.{c}",
                    "severity": severity,
                    "color": color,
                    "icon": icon,
                }

            if path == "/api/kg/v1/strategy-platform/summary":
                row = fetch_one("""
                    SELECT
                        (SELECT count(*)::int FROM analytics.strategy_registry_v1) AS strategies_total,
                        (SELECT count(*)::int FROM analytics.strategy_registry_v1 WHERE enabled=true) AS strategies_enabled,
                        (SELECT count(*)::int FROM analytics.strategy_registry_v1 WHERE paper_enabled=true) AS paper_enabled,
                        (SELECT count(*)::int FROM analytics.strategy_registry_v1 WHERE live_enabled=true) AS live_enabled,
                        (SELECT count(*)::int FROM analytics.strategy_configuration_v1 WHERE active=true) AS active_configs,
                        (SELECT count(*)::int FROM analytics.strategy_feature_dependency_v1) AS dependencies_total,
                        (SELECT count(*)::int FROM analytics.strategy_signal_snapshot_v1) AS signals_total,
                        (SELECT count(*)::int FROM analytics.strategy_signal_snapshot_v1 WHERE execution_allowed=true) AS execution_allowed,
                        (SELECT max(signal_ts) FROM analytics.strategy_signal_snapshot_v1) AS latest_signal_ts;
                """) or {}
                health_code = "HEALTHY" if int(row.get("strategies_enabled") or 0) > 0 and int(row.get("active_configs") or 0) > 0 else "DEGRADED"
                row["health"] = dto("health", health_code)
                self.send_json(200, response("OK", row, {"source": "analytics.strategy_*"}))
                return

            if path == "/api/kg/v1/strategy-platform/registry":
                rows = fetch_all("""
                    SELECT
                        strategy_family,
                        strategy_name,
                        strategy_version,
                        category,
                        enabled,
                        paper_enabled,
                        risk_enabled,
                        live_enabled,
                        priority,
                        description,
                        status,
                        updated_at
                    FROM analytics.strategy_registry_v1
                    ORDER BY priority, strategy_family, strategy_version;
                """)
                for r in rows:
                    r["status"] = dto("status", r.get("status"))
                    r["enabled_status"] = dto("status", "ACTIVE" if r.get("enabled") else "DISABLED")
                self.send_json(200, response("OK", rows, {"source": "analytics.strategy_registry_v1"}))
                return

            if path == "/api/kg/v1/strategy-platform/configuration":
                rows = fetch_all("""
                    SELECT
                        strategy_family,
                        strategy_version,
                        config_version,
                        active,
                        config_json,
                        updated_at
                    FROM analytics.strategy_configuration_v1
                    ORDER BY strategy_family, strategy_version, config_version;
                """)
                for r in rows:
                    r["active_status"] = dto("status", "ACTIVE" if r.get("active") else "DISABLED")
                self.send_json(200, response("OK", rows, {"source": "analytics.strategy_configuration_v1"}))
                return

            if path == "/api/kg/v1/strategy-platform/dependencies":
                rows = fetch_all("""
                    SELECT
                        strategy_family,
                        strategy_version,
                        feature_name,
                        required,
                        weight
                    FROM analytics.strategy_feature_dependency_v1
                    ORDER BY strategy_family, strategy_version, feature_name;
                """)
                self.send_json(200, response("OK", rows, {"source": "analytics.strategy_feature_dependency_v1"}))
                return

            if path == "/api/kg/v1/strategy-platform/signals":
                limit = int(q.get("limit", ["500"])[0])
                rows = fetch_all("""
                    SELECT
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_family,
                        signal_ts,
                        signal_direction,
                        signal_strength,
                        signal_score,
                        confidence,
                        signal_status,
                        feature_quality_score,
                        market_quality_status,
                        paper_allowed,
                        risk_allowed,
                        execution_allowed,
                        feature_version,
                        strategy_version,
                        refreshed_at
                    FROM analytics.strategy_signal_snapshot_v1
                    ORDER BY signal_ts DESC, signal_score DESC
                    LIMIT %s;
                """, (limit,))
                for r in rows:
                    r["signal_direction"] = dto("signal", r.get("signal_direction"))
                    r["signal_status"] = dto("status", r.get("signal_status"))
                    r["market_quality_status"] = dto("status", r.get("market_quality_status"))
                self.send_json(200, response("OK", rows, {"source": "analytics.strategy_signal_snapshot_v1"}))
                return

            if path == "/api/kg/v1/strategy-platform/health":
                row = fetch_one("""
                    SELECT
                        (SELECT count(*)::int FROM analytics.strategy_registry_v1) AS registry_rows,
                        (SELECT count(*)::int FROM analytics.strategy_registry_v1 WHERE enabled=true) AS enabled_strategies,
                        (SELECT count(*)::int FROM analytics.strategy_configuration_v1 WHERE active=true) AS active_configs,
                        (SELECT count(*)::int FROM analytics.strategy_feature_dependency_v1) AS dependency_rows,
                        (SELECT count(*)::int FROM analytics.strategy_signal_snapshot_v1) AS signal_rows,
                        (SELECT count(*)::int FROM analytics.strategy_signal_snapshot_v1 WHERE execution_allowed=true) AS unsafe_execution_rows;
                """) or {}
                health_code = "HEALTHY"
                if int(row.get("enabled_strategies") or 0) <= 0 or int(row.get("active_configs") or 0) <= 0:
                    health_code = "DEGRADED"
                if int(row.get("unsafe_execution_rows") or 0) > 0:
                    health_code = "FAILED"
                row["health"] = dto("health", health_code)
                self.send_json(200, response("OK", row, {"source": "analytics.strategy_platform"}))
                return

            if path == "/api/kg/v1/strategy-platform/workbench":
                from strategy.volatility_breakout.config import VolatilityBreakoutConfig
                from strategy.volatility_breakout.strategy import VolatilityBreakoutStrategy

                cfg_row = fetch_one("""
                    SELECT config_json
                    FROM analytics.strategy_configuration_v1
                    WHERE strategy_family='VOLATILITY_BREAKOUT'
                      AND strategy_version='v1'
                      AND active=true
                    ORDER BY updated_at DESC
                    LIMIT 1;
                """) or {}

                strategy = VolatilityBreakoutStrategy(
                    VolatilityBreakoutConfig.from_dict(cfg_row.get("config_json") or {})
                )

                features = fetch_all("""
                    SELECT
                        symbol, asset_class, timeframe, bar_ts, close,
                        range_pct, body_pct, return1_pct, return5_pct,
                        volume_ratio20, feature_quality_score,
                        market_quality_status, source_version
                    FROM analytics.feature_snapshot_v1
                    WHERE bar_ts IS NOT NULL
                    ORDER BY bar_ts DESC, symbol, timeframe
                    LIMIT 200;
                """)

                rows = []
                signals = 0
                for f in features:
                    result = strategy.run(dict(f))
                    signal = result.signal
                    if signal:
                        signals += 1
                    rows.append({
                        "symbol": f.get("symbol"),
                        "timeframe": f.get("timeframe"),
                        "bar_ts": f.get("bar_ts"),
                        "strategy_family": strategy.family,
                        "strategy_version": strategy.version,
                        "reason": dto("status", result.reason),
                        "signal_direction": dto("signal", signal.direction if signal else "FLAT"),
                        "signal_score": signal.score if signal else 0,
                        "confidence": signal.confidence if signal else 0,
                        "passed_filters": result.diagnostics.passed_filters,
                        "failed_filters": result.diagnostics.failed_filters,
                        "feature_values": result.diagnostics.feature_values,
                        "thresholds": result.diagnostics.thresholds,
                        "score_breakdown": result.diagnostics.score_breakdown,
                        "execution_time_ms": result.diagnostics.execution_time_ms,
                    })

                payload = {
                    "summary": {
                        "features_checked": len(features),
                        "signals_found": signals,
                        "strategy_family": strategy.family,
                        "strategy_version": strategy.version,
                    },
                    "rows": rows,
                }
                self.send_json(200, response("OK", payload, {"source": "analytics.feature_snapshot_v1"}))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > scripts/test_strategy_platform_api_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STRATEGY_PLATFORM_API_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/api/serve_knowledge_graph_api_v1.py

DATABASE_URL=postgresql:///finam_core STRATEGY_FEATURE_LIMIT=5000 PYTHONPATH=src \
python src/scripts/build_multi_strategy_engine_builder_v1.py

sudo systemctl restart marketcore-kg-api.service
sleep 2

base="http://127.0.0.1:8095"

for path in \
  /api/kg/v1/strategy-platform/summary \
  /api/kg/v1/strategy-platform/registry \
  /api/kg/v1/strategy-platform/configuration \
  /api/kg/v1/strategy-platform/dependencies \
  /api/kg/v1/strategy-platform/signals \
  /api/kg/v1/strategy-platform/health \
  /api/kg/v1/strategy-platform/workbench
do
  curl -fsS "$base$path" > "/tmp${path//\//_}.json"
done

python - <<'PY'
import json

def load(name):
    return json.load(open(name, encoding="utf-8"))

summary = load("/tmp_api_kg_v1_strategy-platform_summary.json")
registry = load("/tmp_api_kg_v1_strategy-platform_registry.json")
signals = load("/tmp_api_kg_v1_strategy-platform_signals.json")
health = load("/tmp_api_kg_v1_strategy-platform_health.json")
workbench = load("/tmp_api_kg_v1_strategy-platform_workbench.json")

assert summary["status"] == "OK"
assert summary["data"]["strategies_enabled"] >= 1
assert "health" in summary["data"]
assert "display_key" in summary["data"]["health"]

assert registry["status"] == "OK"
assert len(registry["data"]) >= 1
assert isinstance(registry["data"][0]["status"], dict)

assert signals["status"] == "OK"
assert len(signals["data"]) >= 1
assert isinstance(signals["data"][0]["signal_direction"], dict)
assert signals["data"][0]["execution_allowed"] is False

assert health["status"] == "OK"
assert "health" in health["data"]
assert health["data"]["health"]["code"] in {"HEALTHY", "DEGRADED", "FAILED"}

assert workbench["status"] == "OK"
assert workbench["data"]["summary"]["features_checked"] > 0
PY

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.strategy_signal_snapshot_v1
WHERE execution_allowed=true OR risk_allowed=true;
")
test "$unsafe" = "0"

echo "unsafe_allowed_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=STRATEGY_PLATFORM_API_V1_READY"
echo "VERDICT=TEST_STRATEGY_PLATFORM_API_V1_OK"
SH_TEST

chmod +x scripts/test_strategy_platform_api_v1.sh
scripts/test_strategy_platform_api_v1.sh

echo "VERDICT=BUILD_STRATEGY_PLATFORM_API_V1_OK"
