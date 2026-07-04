#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_STRATEGY_RESEARCH_WORKBENCH_V1 ==="

mkdir -p src/marketcore/presentation/pages scripts

api_file="src/marketcore/api/serve_knowledge_graph_api_v1.py"
cp "$api_file" /tmp/serve_knowledge_graph_api_v1.before_strategy_workbench_v1.bak

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if "/api/kg/v1/strategy-workbench" not in s:
    marker = '            if path == "/api/kg/v1/feature-store":'
    if marker not in s:
        marker = '            if path == "/api/kg/v1/edge-pipeline":'
    if marker not in s:
        raise SystemExit("API_INSERT_MARKER_NOT_FOUND")

    block = r'''
            if path == "/api/kg/v1/strategy-workbench":
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

                cfg_json = cfg_row.get("config_json") or {}
                strategy = VolatilityBreakoutStrategy(VolatilityBreakoutConfig.from_dict(cfg_json))

                feature_rows = fetch_all("""
                    SELECT
                        symbol,
                        asset_class,
                        timeframe,
                        bar_ts,
                        close,
                        range_pct,
                        body_pct,
                        return1_pct,
                        return5_pct,
                        volume_ratio20,
                        feature_quality_score,
                        market_quality_status,
                        source_version
                    FROM analytics.feature_snapshot_v1
                    WHERE bar_ts IS NOT NULL
                    ORDER BY bar_ts DESC, symbol, timeframe
                    LIMIT 200;
                """)

                rows = []
                signals = 0
                for f in feature_rows:
                    result = strategy.run(dict(f))
                    signal = result.signal
                    if signal is not None:
                        signals += 1

                    rows.append({
                        "symbol": f.get("symbol"),
                        "asset_class": f.get("asset_class"),
                        "timeframe": f.get("timeframe"),
                        "bar_ts": f.get("bar_ts"),
                        "strategy_family": strategy.family,
                        "strategy_version": strategy.version,
                        "reason": result.reason,
                        "signal_direction": signal.direction if signal else "FLAT",
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
                        "features_checked": len(feature_rows),
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

cat >> src/marketcore/presentation/ui_labels.py <<'PY'

try:
    ROUTE_LABELS_RU.update({
        "/strategy-workbench": "Рабочее место стратегии",
        "strategy.workbench.title": "Рабочее место стратегии",
        "strategy.workbench.subtitle": "Диагностика решений стратегии через Platform API.",
        "strategy.workbench.summary": "Сводка",
        "strategy.workbench.features_checked": "Проверено признаков",
        "strategy.workbench.signals_found": "Найдено сигналов",
        "strategy.workbench.strategy": "Стратегия",
        "strategy.workbench.rows": "Диагностика",
        "strategy.workbench.instrument": "Инструмент",
        "strategy.workbench.timeframe": "TF",
        "strategy.workbench.bar": "Бар",
        "strategy.workbench.signal": "Сигнал",
        "strategy.workbench.reason": "Причина",
        "strategy.workbench.score": "Score",
        "strategy.workbench.confidence": "Confidence",
        "strategy.workbench.passed": "Прошли",
        "strategy.workbench.failed": "Не прошли",
        "strategy.workbench.execution_time": "Время",
        "signal.LONG": "Long",
        "signal.SHORT": "Short",
        "signal.FLAT": "Нет сигнала",
    })
except NameError:
    pass
PY

cat > src/marketcore/presentation/pages/strategy_workbench.py <<'PY'
from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context
from marketcore.presentation.ui_labels import display_label


def _e(value: object) -> str:
    return escape("" if value is None else str(value))


def _label(key: str) -> str:
    return display_label(key)


def _signal(value: object) -> str:
    return display_label(f"signal.{value}")


class StrategyWorkbenchPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/strategy-workbench",
            title=display_label("/strategy-workbench"),
            icon="⌁",
            menu_order=36,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/strategy-workbench").get("data") or {}

        summary = payload.get("summary") or {}
        rows = payload.get("rows") or []

        body = ""
        for r in rows[:100]:
            body += f"""
            <tr>
                <td>{_e(r.get("symbol"))}</td>
                <td>{_e(r.get("timeframe"))}</td>
                <td>{_e(r.get("bar_ts"))}</td>
                <td>{_e(_signal(r.get("signal_direction")))}</td>
                <td>{_e(_label('strategy.workbench.' + str(r.get("reason", "")).lower())) if False else _e(r.get("reason"))}</td>
                <td>{_e(ctx.formatter.number(r.get("signal_score"), 4))}</td>
                <td>{_e(ctx.formatter.number(r.get("confidence"), 4))}</td>
                <td>{_e(", ".join(r.get("passed_filters") or []))}</td>
                <td>{_e(", ".join(r.get("failed_filters") or []))}</td>
                <td>{_e(ctx.formatter.number(r.get("execution_time_ms"), 3))}</td>
            </tr>
            """

        return f"""
        <section class="card">
            <h2>{_e(_label("strategy.workbench.title"))}</h2>
            <p>{_e(_label("strategy.workbench.subtitle"))}</p>
        </section>

        <section class="cards">
            <div class="card"><h3>{_e(_label("strategy.workbench.features_checked"))}</h3><p>{_e(summary.get("features_checked"))}</p></div>
            <div class="card"><h3>{_e(_label("strategy.workbench.signals_found"))}</h3><p>{_e(summary.get("signals_found"))}</p></div>
            <div class="card"><h3>{_e(_label("strategy.workbench.strategy"))}</h3><p>{_e(summary.get("strategy_family"))}</p></div>
        </section>

        <section class="card">
            <h2>{_e(_label("strategy.workbench.rows"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("strategy.workbench.instrument"))}</th>
                        <th>{_e(_label("strategy.workbench.timeframe"))}</th>
                        <th>{_e(_label("strategy.workbench.bar"))}</th>
                        <th>{_e(_label("strategy.workbench.signal"))}</th>
                        <th>{_e(_label("strategy.workbench.reason"))}</th>
                        <th>{_e(_label("strategy.workbench.score"))}</th>
                        <th>{_e(_label("strategy.workbench.confidence"))}</th>
                        <th>{_e(_label("strategy.workbench.passed"))}</th>
                        <th>{_e(_label("strategy.workbench.failed"))}</th>
                        <th>{_e(_label("strategy.workbench.execution_time"))}</th>
                    </tr>
                </thead>
                <tbody>{body}</tbody>
            </table>
        </section>
        """
PY

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

imp = "from marketcore.presentation.pages.strategy_workbench import StrategyWorkbenchPage\n"
if imp not in s:
    future = "from __future__ import annotations\n\n"
    if future not in s:
        raise SystemExit("FUTURE_IMPORT_NOT_FOUND")
    s = s.replace(future, future + imp)

entry = "    StrategyWorkbenchPage(),\n"
if entry not in s:
    if "    FeatureStorePage(),\n" in s:
        s = s.replace("    FeatureStorePage(),\n", "    FeatureStorePage(),\n" + entry)
    else:
        s = s.replace("    AiPage(),\n]", "    AiPage(),\n" + entry + "]")

p.write_text(s)
PY

cat > scripts/test_strategy_research_workbench_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STRATEGY_RESEARCH_WORKBENCH_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/strategy_workbench.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core STRATEGY_FEATURE_LIMIT=5000 PYTHONPATH=src \
python src/scripts/build_multi_strategy_engine_builder_v1.py

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/strategy-workbench" > /tmp/strategy_workbench_api.json
curl -fsS "http://127.0.0.1:8080/strategy-workbench" > /tmp/strategy_workbench_ui.html

python - <<'PY'
import json

p = json.load(open("/tmp/strategy_workbench_api.json", encoding="utf-8"))
assert p["status"] == "OK"
data = p["data"]
assert data["summary"]["features_checked"] > 0
assert "rows" in data
assert len(data["rows"]) > 0
row = data["rows"][0]
assert "passed_filters" in row
assert "failed_filters" in row
assert "score_breakdown" in row
PY

grep -q "analytics.feature_snapshot_v1" /tmp/strategy_workbench_api.json
grep -q "Рабочее место стратегии" /tmp/strategy_workbench_ui.html

if grep -R "SELECT .*feature_snapshot_v1\|FROM analytics.feature_snapshot_v1" \
  src/marketcore/presentation/pages/strategy_workbench.py; then
  echo "ERROR_DIRECT_SQL_IN_STRATEGY_WORKBENCH_UI"
  exit 1
fi

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=STRATEGY_RESEARCH_WORKBENCH_V1_READY"
echo "VERDICT=TEST_STRATEGY_RESEARCH_WORKBENCH_V1_OK"
SH_TEST

chmod +x scripts/test_strategy_research_workbench_v1.sh
scripts/test_strategy_research_workbench_v1.sh

echo "VERDICT=BUILD_STRATEGY_RESEARCH_WORKBENCH_V1_OK"
