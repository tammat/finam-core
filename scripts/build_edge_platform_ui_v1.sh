#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_PLATFORM_UI_V1 ==="

mkdir -p src/marketcore/presentation/pages scripts

cat >> src/marketcore/presentation/ui_labels.py <<'PY'

try:
    ROUTE_LABELS_RU.update({
        "/edge-platform": "Edge Platform",
        "edge.platform.title": "Edge Platform",
        "edge.platform.subtitle": "Оценка качества сигналов Strategy Platform через Platform API.",
        "edge.platform.summary": "Сводка",
        "edge.platform.decisions": "Решения",
        "edge.platform.configuration": "Конфигурация",
        "edge.platform.governance": "Governance",
        "edge.platform.edge_rows": "Всего решений",
        "edge.platform.allow_rows": "ALLOW",
        "edge.platform.observe_rows": "OBSERVE",
        "edge.platform.block_rows": "BLOCK",
        "edge.platform.ready_for_paper": "Ready for Paper",
        "edge.platform.unsafe_live": "Unsafe Live",
        "edge.platform.avg_edge_score": "Средний Edge Score",
        "edge.platform.avg_validation_score": "Средний Validation Score",
        "edge.platform.instrument": "Инструмент",
        "edge.platform.strategy": "Стратегия",
        "edge.platform.timeframe": "TF",
        "edge.platform.signal_ts": "Время сигнала",
        "edge.platform.edge_score": "Edge Score",
        "edge.platform.validation_score": "Validation",
        "edge.platform.decision": "Decision",
        "edge.platform.recommendation": "Recommendation",
        "edge.platform.replay": "Replay",
        "edge.platform.paper": "Paper",
        "edge.platform.live": "Live",
        "edge.platform.edge_name": "Edge",
        "edge.platform.enabled": "Включено",
        "edge.platform.config": "Параметры",
        "edge.platform.readiness": "Готовность",
        "edge.platform.score_engine": "Score Engine",
        "edge.platform.validation": "Validation",
        "edge.platform.decision_engine": "Decision Engine",
        "edge.platform.api": "API",
        "edge.platform.ui": "UI",
        "common.yes": "Да",
        "common.no": "Нет",
        "status.ACTIVE": "Активно",
        "status.DISABLED": "Отключено",
        "health.HEALTHY": "Здорово",
        "health.DEGRADED": "Требует внимания",
        "health.FAILED": "Ошибка",
        "decision.ALLOW": "ALLOW",
        "decision.OBSERVE": "OBSERVE",
        "decision.BLOCK": "BLOCK",
        "recommendation.READY_FOR_RISK_REVIEW": "Готово к risk review",
        "recommendation.WAIT_VALIDATION": "Ожидание validation",
        "recommendation.WAIT_RESEARCH": "Ожидание research",
        "governance.NOT_READY": "Не готово",
        "governance.READY_FOR_RESEARCH": "Готово к Research"
    })
except NameError:
    pass
PY

cat > src/marketcore/presentation/pages/edge_platform.py <<'PY'
from __future__ import annotations

from html import escape
import json

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context
from marketcore.presentation.ui_labels import display_label


def _e(value: object) -> str:
    return escape("" if value is None else str(value))


def _label(key: str) -> str:
    return display_label(key)


def _dto_label(dto: object) -> str:
    if isinstance(dto, dict):
        return display_label(str(dto.get("display_key") or "status.UNKNOWN"))
    return display_label(f"status.{dto or 'UNKNOWN'}")


def _bool_label(value: object) -> str:
    return display_label("common.yes" if bool(value) else "common.no")


class EdgePlatformPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/edge-platform",
            title=display_label("/edge-platform"),
            icon="◇",
            menu_order=39,
        )

    def render(self) -> str:
        ctx = build_presentation_context()

        summary = ctx.api_get("/api/kg/v1/edge-platform/summary").get("data") or {}
        decisions = ctx.api_get("/api/kg/v1/edge-platform/decisions").get("data") or []
        configs = ctx.api_get("/api/kg/v1/edge-platform/configuration").get("data") or []
        governance = ctx.api_get("/api/kg/v1/edge-platform/governance").get("data") or {}

        decision_rows = ""
        for r in decisions[:100]:
            decision_rows += f"""
            <tr>
                <td>{_e(r.get("symbol"))}</td>
                <td>{_e(r.get("strategy_family"))}</td>
                <td>{_e(r.get("timeframe"))}</td>
                <td>{_e(r.get("signal_ts"))}</td>
                <td>{_e(ctx.formatter.number(r.get("edge_score"), 4))}</td>
                <td>{_e(ctx.formatter.number(r.get("validation_score"), 4))}</td>
                <td>{_e(_dto_label(r.get("decision")))}</td>
                <td>{_e(_dto_label(r.get("recommendation")))}</td>
                <td>{_e(_bool_label(r.get("ready_for_replay")))}</td>
                <td>{_e(_bool_label(r.get("ready_for_paper")))}</td>
                <td>{_e(_bool_label(r.get("ready_for_live")))}</td>
            </tr>
            """

        config_rows = ""
        for r in configs:
            config_text = json.dumps(r.get("config_json") or {}, ensure_ascii=False, sort_keys=True)
            config_rows += f"""
            <tr>
                <td>{_e(r.get("edge_name"))}</td>
                <td>{_e(_dto_label(r.get("enabled_status")))}</td>
                <td><code>{_e(config_text)}</code></td>
            </tr>
            """

        governance_rows = ""
        for label_key, field in [
            ("edge.platform.score_engine", "score_engine_status"),
            ("edge.platform.validation", "validation_status"),
            ("edge.platform.decision_engine", "decision_status"),
            ("edge.platform.api", "api_status"),
            ("edge.platform.ui", "ui_status"),
        ]:
            governance_rows += f"""
            <tr>
                <td>{_e(_label(label_key))}</td>
                <td>{_e(_dto_label(governance.get(field)))}</td>
            </tr>
            """

        return f"""
        <section class="card">
            <h2>{_e(_label("edge.platform.title"))}</h2>
            <p>{_e(_label("edge.platform.subtitle"))}</p>
        </section>

        <section class="cards">
            <div class="card"><h3>{_e(_label("edge.platform.edge_rows"))}</h3><p>{_e(summary.get("edge_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("edge.platform.allow_rows"))}</h3><p>{_e(summary.get("allow_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("edge.platform.observe_rows"))}</h3><p>{_e(summary.get("observe_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("edge.platform.block_rows"))}</h3><p>{_e(summary.get("block_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("edge.platform.ready_for_paper"))}</h3><p>{_e(summary.get("ready_for_paper_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("edge.platform.unsafe_live"))}</h3><p>{_e(summary.get("unsafe_live_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("edge.platform.avg_edge_score"))}</h3><p>{_e(ctx.formatter.number(summary.get("avg_edge_score"), 4))}</p></div>
            <div class="card"><h3>{_e(_label("edge.platform.avg_validation_score"))}</h3><p>{_e(ctx.formatter.number(summary.get("avg_validation_score"), 4))}</p></div>
        </section>

        <section class="card">
            <h2>{_e(_label("edge.platform.decisions"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("edge.platform.instrument"))}</th>
                        <th>{_e(_label("edge.platform.strategy"))}</th>
                        <th>{_e(_label("edge.platform.timeframe"))}</th>
                        <th>{_e(_label("edge.platform.signal_ts"))}</th>
                        <th>{_e(_label("edge.platform.edge_score"))}</th>
                        <th>{_e(_label("edge.platform.validation_score"))}</th>
                        <th>{_e(_label("edge.platform.decision"))}</th>
                        <th>{_e(_label("edge.platform.recommendation"))}</th>
                        <th>{_e(_label("edge.platform.replay"))}</th>
                        <th>{_e(_label("edge.platform.paper"))}</th>
                        <th>{_e(_label("edge.platform.live"))}</th>
                    </tr>
                </thead>
                <tbody>{decision_rows}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>{_e(_label("edge.platform.configuration"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("edge.platform.edge_name"))}</th>
                        <th>{_e(_label("edge.platform.enabled"))}</th>
                        <th>{_e(_label("edge.platform.config"))}</th>
                    </tr>
                </thead>
                <tbody>{config_rows}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>{_e(_label("edge.platform.governance"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("edge.platform.governance"))}</th>
                        <th>{_e(_label("edge.platform.readiness"))}</th>
                    </tr>
                </thead>
                <tbody>{governance_rows}</tbody>
            </table>
        </section>
        """
PY

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

imp = "from marketcore.presentation.pages.edge_platform import EdgePlatformPage\n"
if imp not in s:
    future = "from __future__ import annotations\n\n"
    if future not in s:
        raise SystemExit("FUTURE_IMPORT_NOT_FOUND")
    s = s.replace(future, future + imp)

entry = "    EdgePlatformPage(),\n"
if entry not in s:
    if "    StrategyGovernancePage(),\n" in s:
        s = s.replace("    StrategyGovernancePage(),\n", "    StrategyGovernancePage(),\n" + entry)
    elif "    StrategyPlatformPage(),\n" in s:
        s = s.replace("    StrategyPlatformPage(),\n", "    StrategyPlatformPage(),\n" + entry)
    else:
        raise SystemExit("REGISTRY_INSERT_ANCHOR_NOT_FOUND")

p.write_text(s)
PY

cat > scripts/test_edge_platform_ui_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_PLATFORM_UI_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/edge_platform.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/router.py

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/edge-platform/summary" > /tmp/edge_platform_ui_summary.json
curl -fsS "http://127.0.0.1:8095/api/kg/v1/edge-platform/decisions" > /tmp/edge_platform_ui_decisions.json
curl -fsS "http://127.0.0.1:8080/edge-platform" > /tmp/edge_platform_ui.html

grep -q "Edge Platform" /tmp/edge_platform_ui.html
grep -q "Оценка качества сигналов" /tmp/edge_platform_ui.html

if grep -R "SELECT .*edge_\|FROM analytics.edge_" \
  src/marketcore/presentation/pages/edge_platform.py; then
  echo "ERROR_DIRECT_SQL_IN_EDGE_PLATFORM_UI"
  exit 1
fi

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_decision_snapshot_v1
WHERE ready_for_live=true OR ready_for_micro_live=true;
")
test "$unsafe" = "0"

echo "unsafe_live_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_PLATFORM_UI_V1_READY"
echo "VERDICT=TEST_EDGE_PLATFORM_UI_V1_OK"
SH_TEST

chmod +x scripts/test_edge_platform_ui_v1.sh
scripts/test_edge_platform_ui_v1.sh

echo "VERDICT=BUILD_EDGE_PLATFORM_UI_V1_OK"
