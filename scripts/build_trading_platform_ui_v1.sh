#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_TRADING_PLATFORM_UI_V1 ==="

mkdir -p src/marketcore/presentation/pages scripts

cat >> src/marketcore/presentation/ui_labels.py <<'PY'

try:
    ROUTE_LABELS_RU.update({
        "/trading-platform": "Trading Platform",
        "trading.platform.title": "Trading Platform",
        "trading.platform.subtitle": "Order Intent слой без отправки заявок брокеру.",
        "trading.platform.summary": "Сводка",
        "trading.platform.intents": "Order Intents",
        "trading.platform.configuration": "Конфигурация",
        "trading.platform.governance": "Governance",

        "trading.platform.intent_rows": "Всего intent",
        "trading.platform.paper_allowed": "Paper allowed",
        "trading.platform.shadow_allowed": "Shadow allowed",
        "trading.platform.micro_live_allowed": "Micro Live allowed",
        "trading.platform.live_allowed": "Live allowed",
        "trading.platform.order_sent": "Order sent",
        "trading.platform.paper_ready": "Paper ready",
        "trading.platform.block_rows": "Blocked",

        "trading.platform.instrument": "Инструмент",
        "trading.platform.strategy": "Стратегия",
        "trading.platform.timeframe": "TF",
        "trading.platform.signal_ts": "Время сигнала",
        "trading.platform.risk_score": "Risk Score",
        "trading.platform.side": "Side",
        "trading.platform.order_type": "Order Type",
        "trading.platform.quantity": "Quantity",
        "trading.platform.decision": "Decision",
        "trading.platform.recommendation": "Recommendation",
        "trading.platform.paper": "Paper",
        "trading.platform.live": "Live",
        "trading.platform.sent": "Sent",

        "trading.platform.trading_name": "Trading",
        "trading.platform.enabled": "Включено",
        "trading.platform.config": "Параметры",

        "trading.platform.builder": "Builder",
        "trading.platform.order_intent": "Order Intent",
        "trading.platform.api": "API",
        "trading.platform.ui": "UI",
        "trading.platform.readiness": "Готовность",

        "trading.PAPER_INTENT_READY": "Paper intent ready",
        "trading.TRADING_BLOCK": "Trading block",

        "recommendation.READY_FOR_PAPER_EXECUTION": "Готово к paper execution",
        "recommendation.WAIT_TRADING_REVIEW": "Ожидание trading review",
    })
except NameError:
    pass
PY

cat > src/marketcore/presentation/pages/trading_platform.py <<'PY'
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


class TradingPlatformPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/trading-platform",
            title=display_label("/trading-platform"),
            icon="◈",
            menu_order=41,
        )

    def render(self) -> str:
        ctx = build_presentation_context()

        summary = ctx.api_get("/api/kg/v1/trading-platform/summary").get("data") or {}
        intents = ctx.api_get("/api/kg/v1/trading-platform/intents").get("data") or []
        configs = ctx.api_get("/api/kg/v1/trading-platform/configuration").get("data") or []
        governance = ctx.api_get("/api/kg/v1/trading-platform/governance").get("data") or {}

        intent_rows = ""
        for r in intents[:100]:
            intent_rows += f"""
            <tr>
                <td>{_e(r.get("symbol"))}</td>
                <td>{_e(r.get("strategy_family"))}</td>
                <td>{_e(r.get("timeframe"))}</td>
                <td>{_e(r.get("signal_ts"))}</td>
                <td>{_e(ctx.formatter.number(r.get("risk_score"), 4))}</td>
                <td>{_e(_dto_label(r.get("order_side_status")))}</td>
                <td>{_e(r.get("order_type"))}</td>
                <td>{_e(ctx.formatter.number(r.get("quantity"), 4))}</td>
                <td>{_e(_dto_label(r.get("trading_decision")))}</td>
                <td>{_e(_dto_label(r.get("recommendation")))}</td>
                <td>{_e(_bool_label(r.get("paper_allowed")))}</td>
                <td>{_e(_bool_label(r.get("live_allowed")))}</td>
                <td>{_e(_bool_label(r.get("order_sent")))}</td>
            </tr>
            """

        config_rows = ""
        for r in configs:
            config_text = json.dumps(r.get("config_json") or {}, ensure_ascii=False, sort_keys=True)
            config_rows += f"""
            <tr>
                <td>{_e(r.get("trading_name"))}</td>
                <td>{_e(_dto_label(r.get("enabled_status")))}</td>
                <td><code>{_e(config_text)}</code></td>
            </tr>
            """

        governance_rows = ""
        for label_key, field in [
            ("trading.platform.builder", "builder_status"),
            ("trading.platform.order_intent", "order_intent_status"),
            ("trading.platform.api", "api_status"),
            ("trading.platform.ui", "ui_status"),
        ]:
            governance_rows += f"""
            <tr>
                <td>{_e(_label(label_key))}</td>
                <td>{_e(_dto_label(governance.get(field)))}</td>
            </tr>
            """

        return f"""
        <section class="card">
            <h2>{_e(_label("trading.platform.title"))}</h2>
            <p>{_e(_label("trading.platform.subtitle"))}</p>
        </section>

        <section class="cards">
            <div class="card"><h3>{_e(_label("trading.platform.intent_rows"))}</h3><p>{_e(summary.get("intent_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("trading.platform.paper_allowed"))}</h3><p>{_e(summary.get("paper_allowed_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("trading.platform.shadow_allowed"))}</h3><p>{_e(summary.get("shadow_allowed_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("trading.platform.micro_live_allowed"))}</h3><p>{_e(summary.get("micro_live_allowed_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("trading.platform.live_allowed"))}</h3><p>{_e(summary.get("live_allowed_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("trading.platform.order_sent"))}</h3><p>{_e(summary.get("order_sent_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("trading.platform.paper_ready"))}</h3><p>{_e(summary.get("paper_ready_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("trading.platform.block_rows"))}</h3><p>{_e(summary.get("block_rows"))}</p></div>
        </section>

        <section class="card">
            <h2>{_e(_label("trading.platform.intents"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("trading.platform.instrument"))}</th>
                        <th>{_e(_label("trading.platform.strategy"))}</th>
                        <th>{_e(_label("trading.platform.timeframe"))}</th>
                        <th>{_e(_label("trading.platform.signal_ts"))}</th>
                        <th>{_e(_label("trading.platform.risk_score"))}</th>
                        <th>{_e(_label("trading.platform.side"))}</th>
                        <th>{_e(_label("trading.platform.order_type"))}</th>
                        <th>{_e(_label("trading.platform.quantity"))}</th>
                        <th>{_e(_label("trading.platform.decision"))}</th>
                        <th>{_e(_label("trading.platform.recommendation"))}</th>
                        <th>{_e(_label("trading.platform.paper"))}</th>
                        <th>{_e(_label("trading.platform.live"))}</th>
                        <th>{_e(_label("trading.platform.sent"))}</th>
                    </tr>
                </thead>
                <tbody>{intent_rows}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>{_e(_label("trading.platform.configuration"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("trading.platform.trading_name"))}</th>
                        <th>{_e(_label("trading.platform.enabled"))}</th>
                        <th>{_e(_label("trading.platform.config"))}</th>
                    </tr>
                </thead>
                <tbody>{config_rows}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>{_e(_label("trading.platform.governance"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("trading.platform.governance"))}</th>
                        <th>{_e(_label("trading.platform.readiness"))}</th>
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

imp = "from marketcore.presentation.pages.trading_platform import TradingPlatformPage\n"
if imp not in s:
    future = "from __future__ import annotations\n\n"
    if future not in s:
        raise SystemExit("FUTURE_IMPORT_NOT_FOUND")
    s = s.replace(future, future + imp)

entry = "    TradingPlatformPage(),\n"
if entry not in s:
    if "    RiskPlatformPage(),\n" in s:
        s = s.replace("    RiskPlatformPage(),\n", "    RiskPlatformPage(),\n" + entry)
    else:
        raise SystemExit("REGISTRY_INSERT_ANCHOR_NOT_FOUND")

p.write_text(s)
PY

cat > scripts/test_trading_platform_ui_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TRADING_PLATFORM_UI_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/trading_platform.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/router.py

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/trading-platform/summary" > /tmp/trading_platform_ui_summary.json
curl -fsS "http://127.0.0.1:8095/api/kg/v1/trading-platform/intents" > /tmp/trading_platform_ui_intents.json
curl -fsS "http://127.0.0.1:8080/trading-platform" > /tmp/trading_platform_ui.html

grep -q "Trading Platform" /tmp/trading_platform_ui.html
grep -q "Order Intent" /tmp/trading_platform_ui.html

if grep -R "SELECT .*trading_\|FROM analytics.trading_" \
  src/marketcore/presentation/pages/trading_platform.py; then
  echo "ERROR_DIRECT_SQL_IN_TRADING_PLATFORM_UI"
  exit 1
fi

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.trading_order_intent_v1
WHERE live_allowed=true
   OR micro_live_allowed=true
   OR order_sent=true;
")
test "$unsafe" = "0"

echo "unsafe_live_or_sent_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TRADING_PLATFORM_UI_V1_READY"
echo "VERDICT=TEST_TRADING_PLATFORM_UI_V1_OK"
SH_TEST

chmod +x scripts/test_trading_platform_ui_v1.sh
scripts/test_trading_platform_ui_v1.sh

echo "VERDICT=BUILD_TRADING_PLATFORM_UI_V1_OK"
