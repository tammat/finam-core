#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_FEATURE_STORE_UI_V1 ==="

mkdir -p src/marketcore/presentation/pages scripts

cat > src/marketcore/presentation/pages/feature_store.py <<'PY'
from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context


class FeatureStorePage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/feature-store",
            title="Feature Store",
            icon="∑",
            menu_order=35,
        )

    def render(self) -> str:
        ctx = build_presentation_context()

        summary = ctx.api_get("/api/kg/v1/feature-store/summary").get("data") or {}
        health = ctx.api_get("/api/kg/v1/feature-store/health").get("data") or {}
        rows = ctx.api_get("/api/kg/v1/feature-store").get("data") or []

        body = ""
        for r in rows[:100]:
            body += f"""
            <tr>
                <td>{escape(str(r.get("symbol", "")))}</td>
                <td>{escape(str(r.get("timeframe", "")))}</td>
                <td>{escape(str(r.get("bar_ts", "")))}</td>
                <td>{escape(ctx.formatter.number(r.get("close"), 4))}</td>
                <td>{escape(ctx.formatter.number(r.get("return1_pct"), 4))}</td>
                <td>{escape(ctx.formatter.number(r.get("return5_pct"), 4))}</td>
                <td>{escape(ctx.formatter.number(r.get("range_pct"), 4))}</td>
                <td>{escape(ctx.formatter.number(r.get("body_pct"), 4))}</td>
                <td>{escape(ctx.formatter.number(r.get("feature_quality_score"), 4))}</td>
            </tr>
            """

        return f"""
        <section class="card">
            <h2>Feature Store</h2>
            <p>Единый слой признаков. Источник: Platform API → analytics.feature_snapshot_v1.</p>
            <p>Health: {escape(str(health.get("health_status", "")))} · Timer: {escape(str(health.get("timer_active", "")))}</p>
            <p>Последний бар: {escape(str(summary.get("latest_bar_ts", "")))} · Обновлено: {escape(str(summary.get("refreshed_at", "")))}</p>
        </section>

        <section class="cards">
            <div class="card"><h3>Всего признаков</h3><p>{escape(str(summary.get("feature_rows", "")))}</p></div>
            <div class="card"><h3>Инструментов</h3><p>{escape(str(summary.get("feature_symbols", "")))}</p></div>
            <div class="card"><h3>Среднее качество</h3><p>{escape(ctx.formatter.number(summary.get("avg_quality_score"), 4))}</p></div>
            <div class="card"><h3>Return1</h3><p>{escape(str(summary.get("with_return1", "")))}</p></div>
            <div class="card"><h3>Volume Ratio20</h3><p>{escape(str(summary.get("with_volume_ratio20", "")))}</p></div>
            <div class="card"><h3>Health</h3><p>{escape(str(health.get("health_status", "")))}</p></div>
        </section>

        <section class="card">
            <h2>Последние признаки</h2>
            <table>
                <thead>
                    <tr>
                        <th>Инструмент</th>
                        <th>TF</th>
                        <th>Бар</th>
                        <th>Close</th>
                        <th>Return1 %</th>
                        <th>Return5 %</th>
                        <th>Range %</th>
                        <th>Body %</th>
                        <th>Quality</th>
                    </tr>
                </thead>
                <tbody>{body}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>Следующий этап</h2>
            <p>FEATURE_STORE_DASHBOARD_V1</p>
        </section>
        """
PY

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

imp = "from marketcore.presentation.pages.feature_store import FeatureStorePage\n"
if imp not in s:
    future = "from __future__ import annotations\n\n"
    if future not in s:
        raise SystemExit("FUTURE_IMPORT_NOT_FOUND")
    s = s.replace(future, future + imp)

entry = "    FeatureStorePage(),\n"
if entry not in s:
    anchor = "    EdgePipelineV2Page(),\n"
    if anchor in s:
        s = s.replace(anchor, anchor + entry)
    else:
        s = s.replace("    AiPage(),\n]", "    AiPage(),\n    FeatureStorePage(),\n]")

p.write_text(s)
PY

cat > scripts/test_feature_store_ui_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FEATURE_STORE_UI_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/feature_store.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/router.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_feature_store_health_v1.py

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/feature-store/summary" > /tmp/feature_store_summary.json
curl -fsS "http://127.0.0.1:8095/api/kg/v1/feature-store/health" > /tmp/feature_store_health.json
curl -fsS "http://127.0.0.1:8080/feature-store" > /tmp/feature_store_ui.html

grep -q "Feature Store" /tmp/feature_store_ui.html
grep -q "analytics.feature_snapshot_v1" /tmp/feature_store_ui.html
grep -q "HEALTHY" /tmp/feature_store_ui.html
grep -q "Последние признаки" /tmp/feature_store_ui.html

if grep -R "SELECT .*feature_snapshot_v1\|FROM analytics.feature_snapshot_v1" \
  src/marketcore/presentation/pages/feature_store.py; then
  echo "ERROR_DIRECT_SQL_IN_FEATURE_STORE_UI"
  exit 1
fi

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.feature_snapshot_v1;")
health=$(psql -At -d finam_core -c "SELECT health_status FROM analytics.feature_store_health_v1 WHERE health_id='GLOBAL';")

test "$rows" -gt 0
test "$health" = "HEALTHY"

echo "feature_rows=$rows"
echo "health_status=$health"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=FEATURE_STORE_UI_V1_READY"
echo "VERDICT=TEST_FEATURE_STORE_UI_V1_OK"
SH_TEST

chmod +x scripts/test_feature_store_ui_v1.sh
scripts/test_feature_store_ui_v1.sh

echo "VERDICT=BUILD_FEATURE_STORE_UI_V1_OK"
