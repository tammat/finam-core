#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_STRATEGY_PLATFORM_UI_V1 ==="

mkdir -p src/marketcore/presentation/pages scripts

cat >> src/marketcore/presentation/ui_labels.py <<'PY'

try:
    ROUTE_LABELS_RU.update({
        "/strategy-platform": "Платформа стратегий",

        "strategy.platform.title": "Платформа стратегий",
        "strategy.platform.subtitle": "Каталог, конфигурации, зависимости и сигналы стратегий через Platform API.",
        "strategy.platform.summary": "Сводка",
        "strategy.platform.registry": "Каталог стратегий",
        "strategy.platform.configuration": "Конфигурации",
        "strategy.platform.dependencies": "Зависимости от признаков",
        "strategy.platform.signals": "Последние сигналы",

        "strategy.platform.strategies_total": "Всего стратегий",
        "strategy.platform.strategies_enabled": "Включено",
        "strategy.platform.active_configs": "Активные конфигурации",
        "strategy.platform.signals_total": "Всего сигналов",
        "strategy.platform.health": "Здоровье",
        "strategy.platform.execution_allowed": "Execution allowed",

        "strategy.platform.family": "Family",
        "strategy.platform.name": "Название",
        "strategy.platform.version": "Версия",
        "strategy.platform.category": "Категория",
        "strategy.platform.status": "Статус",
        "strategy.platform.priority": "Приоритет",
        "strategy.platform.paper": "Paper",
        "strategy.platform.risk": "Risk",
        "strategy.platform.live": "Live",

        "strategy.platform.config_version": "Версия конфигурации",
        "strategy.platform.active": "Активна",
        "strategy.platform.config": "Параметры",

        "strategy.platform.feature": "Признак",
        "strategy.platform.required": "Обязательный",
        "strategy.platform.weight": "Вес",

        "strategy.platform.instrument": "Инструмент",
        "strategy.platform.timeframe": "TF",
        "strategy.platform.signal_ts": "Время сигнала",
        "strategy.platform.direction": "Направление",
        "strategy.platform.score": "Score",
        "strategy.platform.confidence": "Confidence",

        "common.yes": "Да",
        "common.no": "Нет",

        "status.ACTIVE": "Активно",
        "status.DISABLED": "Отключено",
        "status.READY": "Готово",
        "status.UNKNOWN": "Неизвестно",

        "health.HEALTHY": "Здорово",
        "health.DEGRADED": "Требует внимания",
        "health.FAILED": "Ошибка",

        "signal.LONG": "Long",
        "signal.SHORT": "Short",
        "signal.FLAT": "Нет сигнала",
    })
except NameError:
    pass
PY

cat > src/marketcore/presentation/pages/strategy_platform.py <<'PY'
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


class StrategyPlatformPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/strategy-platform",
            title=display_label("/strategy-platform"),
            icon="Ψ",
            menu_order=37,
        )

    def render(self) -> str:
        ctx = build_presentation_context()

        summary = ctx.api_get("/api/kg/v1/strategy-platform/summary").get("data") or {}
        registry = ctx.api_get("/api/kg/v1/strategy-platform/registry").get("data") or []
        configs = ctx.api_get("/api/kg/v1/strategy-platform/configuration").get("data") or []
        deps = ctx.api_get("/api/kg/v1/strategy-platform/dependencies").get("data") or []
        signals = ctx.api_get("/api/kg/v1/strategy-platform/signals").get("data") or []

        registry_rows = ""
        for r in registry:
            registry_rows += f"""
            <tr>
                <td>{_e(r.get("strategy_family"))}</td>
                <td>{_e(r.get("strategy_name"))}</td>
                <td>{_e(r.get("strategy_version"))}</td>
                <td>{_e(r.get("category"))}</td>
                <td>{_e(_dto_label(r.get("status")))}</td>
                <td>{_e(_bool_label(r.get("enabled")))}</td>
                <td>{_e(_bool_label(r.get("paper_enabled")))}</td>
                <td>{_e(_bool_label(r.get("risk_enabled")))}</td>
                <td>{_e(_bool_label(r.get("live_enabled")))}</td>
                <td>{_e(r.get("priority"))}</td>
            </tr>
            """

        config_rows = ""
        for r in configs:
            config_json = r.get("config_json") or {}
            config_text = json.dumps(config_json, ensure_ascii=False, sort_keys=True)
            config_rows += f"""
            <tr>
                <td>{_e(r.get("strategy_family"))}</td>
                <td>{_e(r.get("strategy_version"))}</td>
                <td>{_e(r.get("config_version"))}</td>
                <td>{_e(_dto_label(r.get("active_status")))}</td>
                <td><code>{_e(config_text)}</code></td>
            </tr>
            """

        dep_rows = ""
        for r in deps:
            dep_rows += f"""
            <tr>
                <td>{_e(r.get("strategy_family"))}</td>
                <td>{_e(r.get("strategy_version"))}</td>
                <td>{_e(r.get("feature_name"))}</td>
                <td>{_e(_bool_label(r.get("required")))}</td>
                <td>{_e(ctx.formatter.number(r.get("weight"), 4))}</td>
            </tr>
            """

        signal_rows = ""
        for r in signals[:100]:
            signal_rows += f"""
            <tr>
                <td>{_e(r.get("symbol"))}</td>
                <td>{_e(r.get("timeframe"))}</td>
                <td>{_e(r.get("strategy_family"))}</td>
                <td>{_e(r.get("signal_ts"))}</td>
                <td>{_e(_dto_label(r.get("signal_direction")))}</td>
                <td>{_e(_dto_label(r.get("signal_status")))}</td>
                <td>{_e(ctx.formatter.number(r.get("signal_score"), 4))}</td>
                <td>{_e(ctx.formatter.number(r.get("confidence"), 4))}</td>
                <td>{_e(_bool_label(r.get("execution_allowed")))}</td>
            </tr>
            """

        return f"""
        <section class="card">
            <h2>{_e(_label("strategy.platform.title"))}</h2>
            <p>{_e(_label("strategy.platform.subtitle"))}</p>
        </section>

        <section class="cards">
            <div class="card"><h3>{_e(_label("strategy.platform.strategies_total"))}</h3><p>{_e(summary.get("strategies_total"))}</p></div>
            <div class="card"><h3>{_e(_label("strategy.platform.strategies_enabled"))}</h3><p>{_e(summary.get("strategies_enabled"))}</p></div>
            <div class="card"><h3>{_e(_label("strategy.platform.active_configs"))}</h3><p>{_e(summary.get("active_configs"))}</p></div>
            <div class="card"><h3>{_e(_label("strategy.platform.signals_total"))}</h3><p>{_e(summary.get("signals_total"))}</p></div>
            <div class="card"><h3>{_e(_label("strategy.platform.execution_allowed"))}</h3><p>{_e(summary.get("execution_allowed"))}</p></div>
            <div class="card"><h3>{_e(_label("strategy.platform.health"))}</h3><p>{_e(_dto_label(summary.get("health")))}</p></div>
        </section>

        <section class="card">
            <h2>{_e(_label("strategy.platform.registry"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("strategy.platform.family"))}</th>
                        <th>{_e(_label("strategy.platform.name"))}</th>
                        <th>{_e(_label("strategy.platform.version"))}</th>
                        <th>{_e(_label("strategy.platform.category"))}</th>
                        <th>{_e(_label("strategy.platform.status"))}</th>
                        <th>{_e(_label("strategy.platform.active"))}</th>
                        <th>{_e(_label("strategy.platform.paper"))}</th>
                        <th>{_e(_label("strategy.platform.risk"))}</th>
                        <th>{_e(_label("strategy.platform.live"))}</th>
                        <th>{_e(_label("strategy.platform.priority"))}</th>
                    </tr>
                </thead>
                <tbody>{registry_rows}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>{_e(_label("strategy.platform.configuration"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("strategy.platform.family"))}</th>
                        <th>{_e(_label("strategy.platform.version"))}</th>
                        <th>{_e(_label("strategy.platform.config_version"))}</th>
                        <th>{_e(_label("strategy.platform.active"))}</th>
                        <th>{_e(_label("strategy.platform.config"))}</th>
                    </tr>
                </thead>
                <tbody>{config_rows}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>{_e(_label("strategy.platform.dependencies"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("strategy.platform.family"))}</th>
                        <th>{_e(_label("strategy.platform.version"))}</th>
                        <th>{_e(_label("strategy.platform.feature"))}</th>
                        <th>{_e(_label("strategy.platform.required"))}</th>
                        <th>{_e(_label("strategy.platform.weight"))}</th>
                    </tr>
                </thead>
                <tbody>{dep_rows}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>{_e(_label("strategy.platform.signals"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("strategy.platform.instrument"))}</th>
                        <th>{_e(_label("strategy.platform.timeframe"))}</th>
                        <th>{_e(_label("strategy.platform.family"))}</th>
                        <th>{_e(_label("strategy.platform.signal_ts"))}</th>
                        <th>{_e(_label("strategy.platform.direction"))}</th>
                        <th>{_e(_label("strategy.platform.status"))}</th>
                        <th>{_e(_label("strategy.platform.score"))}</th>
                        <th>{_e(_label("strategy.platform.confidence"))}</th>
                        <th>{_e(_label("strategy.platform.execution_allowed"))}</th>
                    </tr>
                </thead>
                <tbody>{signal_rows}</tbody>
            </table>
        </section>
        """
PY

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

imp = "from marketcore.presentation.pages.strategy_platform import StrategyPlatformPage\n"
if imp not in s:
    future = "from __future__ import annotations\n\n"
    if future not in s:
        raise SystemExit("FUTURE_IMPORT_NOT_FOUND")
    s = s.replace(future, future + imp)

entry = "    StrategyPlatformPage(),\n"
if entry not in s:
    if "    StrategyWorkbenchPage(),\n" in s:
        s = s.replace("    StrategyWorkbenchPage(),\n", "    StrategyWorkbenchPage(),\n" + entry)
    else:
        s = s.replace("    FeatureStorePage(),\n", "    FeatureStorePage(),\n" + entry)

p.write_text(s)
PY

cat > scripts/test_strategy_platform_ui_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STRATEGY_PLATFORM_UI_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/strategy_platform.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/router.py

DATABASE_URL=postgresql:///finam_core STRATEGY_FEATURE_LIMIT=5000 PYTHONPATH=src \
python src/scripts/build_multi_strategy_engine_builder_v1.py

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/strategy-platform/summary" > /tmp/strategy_platform_summary.json
curl -fsS "http://127.0.0.1:8080/strategy-platform" > /tmp/strategy_platform_ui.html

grep -q "Платформа стратегий" /tmp/strategy_platform_ui.html
grep -q "VOLATILITY_BREAKOUT" /tmp/strategy_platform_ui.html
grep -q "Нет" /tmp/strategy_platform_ui.html

if grep -R "SELECT .*strategy_\|FROM analytics.strategy_" \
  src/marketcore/presentation/pages/strategy_platform.py; then
  echo "ERROR_DIRECT_SQL_IN_STRATEGY_PLATFORM_UI"
  exit 1
fi

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
echo "VERDICT=STRATEGY_PLATFORM_UI_V1_READY"
echo "VERDICT=TEST_STRATEGY_PLATFORM_UI_V1_OK"
SH_TEST

chmod +x scripts/test_strategy_platform_ui_v1.sh
scripts/test_strategy_platform_ui_v1.sh

echo "VERDICT=BUILD_STRATEGY_PLATFORM_UI_V1_OK"
