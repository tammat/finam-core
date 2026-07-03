#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts src/marketcore/presentation/pages

cat > sql/marketcore_ui/027_marketcore_ui_route_health_matrix_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.marketcore_ui_route_health_matrix_v1 (
    route TEXT PRIMARY KEY,
    label_ru TEXT NOT NULL DEFAULT '',
    group_key TEXT NOT NULL DEFAULT '',
    group_title_ru TEXT NOT NULL DEFAULT '',
    menu_order INTEGER NOT NULL DEFAULT 0,
    http_status INTEGER NOT NULL DEFAULT 0,
    http_ok BOOLEAN NOT NULL DEFAULT false,
    contains_shell_marker BOOLEAN NOT NULL DEFAULT false,
    content_length INTEGER NOT NULL DEFAULT 0,
    issue TEXT NOT NULL DEFAULT '',
    checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.marketcore_ui_route_health_matrix_v1 TO alex;

COMMIT;

SELECT 'MARKETCORE_UI_ROUTE_HEALTH_MATRIX_SCHEMA_V1_READY' AS verdict;
SQL

cat > scripts/apply_marketcore_ui_route_health_matrix_v1.sh <<'SH_APPLY'
#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql \
  -v ON_ERROR_STOP=1 \
  -d finam_core \
  -f sql/marketcore_ui/027_marketcore_ui_route_health_matrix_v1.sql
SH_APPLY

chmod +x scripts/apply_marketcore_ui_route_health_matrix_v1.sh

cat > src/scripts/build_marketcore_ui_8080_route_health_matrix_v1.py <<'PY'
from __future__ import annotations

import os
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import psycopg2
import psycopg2.extras

from marketcore.presentation.registry import menu_pages
from marketcore.presentation.route_groups import group_for_route
from marketcore.presentation.ui_labels import display_label


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
BASE_URL = os.getenv("MARKETCORE_UI_BASE_URL", "http://127.0.0.1:8080")
SOURCE_VERSION = "MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_V1"


def check_route(route: str) -> dict:
    url = BASE_URL.rstrip("/") + route

    try:
        with urlopen(url, timeout=5) as response:
            body = response.read().decode("utf-8", errors="replace")
            status = int(response.status)
    except HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return {
            "http_status": int(exc.code),
            "http_ok": False,
            "contains_shell_marker": "MARKETCORE_UI_SHELL_V1" in body,
            "content_length": len(body),
            "issue": f"HTTPError:{exc.code}",
        }
    except (URLError, TimeoutError, OSError) as exc:
        return {
            "http_status": 0,
            "http_ok": False,
            "contains_shell_marker": False,
            "content_length": 0,
            "issue": f"{type(exc).__name__}:{exc}",
        }

    contains_shell_marker = "MARKETCORE_UI_SHELL_V1" in body
    http_ok = status == 200 and contains_shell_marker

    return {
        "http_status": status,
        "http_ok": http_ok,
        "contains_shell_marker": contains_shell_marker,
        "content_length": len(body),
        "issue": "" if http_ok else "missing shell marker or non-200",
    }


def main() -> None:
    build_id = str(uuid.uuid4())
    pages = menu_pages()

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_V1 ===")

            cur.execute("DELETE FROM marketcore_ui.marketcore_ui_route_health_matrix_v1;")

            unhealthy = 0

            for page in pages:
                group = group_for_route(page.route)
                result = check_route(page.route)

                if not result["http_ok"]:
                    unhealthy += 1

                cur.execute("""
                    INSERT INTO marketcore_ui.marketcore_ui_route_health_matrix_v1 (
                        route,
                        label_ru,
                        group_key,
                        group_title_ru,
                        menu_order,
                        http_status,
                        http_ok,
                        contains_shell_marker,
                        content_length,
                        issue,
                        checked_at,
                        source_version,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),%s,%s
                    );
                """, (
                    page.route,
                    display_label(page.route, page.title),
                    group.key,
                    group.title_ru,
                    page.menu_order,
                    result["http_status"],
                    result["http_ok"],
                    result["contains_shell_marker"],
                    result["content_length"],
                    result["issue"],
                    SOURCE_VERSION,
                    build_id,
                ))

                print(
                    "ROUTE "
                    f"route={page.route} "
                    f"label={display_label(page.route, page.title)} "
                    f"group={group.key} "
                    f"http_status={result['http_status']} "
                    f"http_ok={int(result['http_ok'])} "
                    f"content_length={result['content_length']} "
                    f"issue={result['issue']}"
                )

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.marketcore_ui_route_health_matrix_v1;")
            rows_written = int(cur.fetchone()["rows"])

    print(f"routes_total={len(pages)}")
    print(f"rows_written={rows_written}")
    print(f"unhealthy_routes={unhealthy}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_V1_READY")


if __name__ == "__main__":
    main()
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/marketcore-ui-route-health-matrix' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/marketcore-ui-route-health-matrix":
                rows = fetch_all("""
                    SELECT
                        route,
                        label_ru,
                        group_key,
                        group_title_ru,
                        menu_order,
                        http_status,
                        http_ok,
                        contains_shell_marker,
                        content_length,
                        issue,
                        checked_at
                    FROM marketcore_ui.marketcore_ui_route_health_matrix_v1
                    ORDER BY group_key, menu_order, route;
                """)
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.marketcore_ui_route_health_matrix_v1",
                    "ui_direct_sql": 0,
                    "logic": "marketcore_ui_8080_route_health_matrix_v1"
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > src/marketcore/presentation/pages/marketcore_ui_route_health_matrix.py <<'PY'
from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context


def _metric(title: str, value: str, note: str = "") -> str:
    return f"""
    <section class="card">
        <h2>{escape(title)}</h2>
        <p style="font-size:28px;font-weight:700;margin:8px 0;">{escape(value)}</p>
        <p>{escape(note)}</p>
    </section>
    """


def _table(rows: list[dict], ctx) -> str:
    if not rows:
        return "<p>Матрица маршрутов пуста.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("group_title_ru", "")))}</td>
            <td><a href="{escape(str(row.get("route", "")))}">{escape(str(row.get("label_ru", "")))}</a></td>
            <td>{escape(str(row.get("route", "")))}</td>
            <td>{escape(str(row.get("http_status", "")))}</td>
            <td>{escape(str(row.get("http_ok", "")))}</td>
            <td>{escape(str(row.get("contains_shell_marker", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("content_length"), 0))}</td>
            <td>{escape(str(row.get("issue", "")))}</td>
        </tr>
        """

    return f"""
    <table>
        <thead>
            <tr>
                <th>Группа</th>
                <th>Страница</th>
                <th>Route</th>
                <th>HTTP</th>
                <th>OK</th>
                <th>Shell</th>
                <th>Размер</th>
                <th>Проблема</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class MarketcoreUiRouteHealthMatrixPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/marketcore-ui-route-health-matrix",
            title="Матрица здоровья маршрутов UI",
            icon="✓",
            menu_order=122,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/marketcore-ui-route-health-matrix")
        rows = payload.get("data") or []

        ok_rows = sum(1 for row in rows if row.get("http_ok") is True)
        bad_rows = len(rows) - ok_rows

        return f"""
        <section class="card">
            <h2>Матрица здоровья маршрутов UI</h2>
            <p>Проверяет, какие страницы MarketCore UI Shell на 8080 реально открываются и содержат shell marker.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.marketcore_ui_route_health_matrix_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;">
            {_metric("Всего маршрутов", ctx.formatter.number(len(rows), 0))}
            {_metric("OK", ctx.formatter.number(ok_rows, 0))}
            {_metric("Проблемы", ctx.formatter.number(bad_rows, 0))}
        </div>

        <section class="card">
            <h2>Маршруты</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Комментарий по рыночным данным</h2>
            <p>Текущий Paper Edge Discovery показывает paper/research-кандидатов. Свежие market data ещё не подключены к этому экрану как отдельный feed.</p>
            <p>Следующий необходимый шаг: PAPER_EDGE_DISCOVERY_MARKET_DATA_BINDING_V1.</p>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/ui_labels.py")
s = p.read_text()

if '"/marketcore-ui-route-health-matrix"' not in s:
    s = s.replace(
        '    "/marketcore-ui-systemd-health": "Здоровье UI и systemd",\n',
        '    "/marketcore-ui-systemd-health": "Здоровье UI и systemd",\n'
        '    "/marketcore-ui-route-health-matrix": "Матрица маршрутов UI",\n',
    )

p.write_text(s)
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/route_groups.py")
s = p.read_text()

if '"/marketcore-ui-route-health-matrix"' not in s:
    s = s.replace(
        '            "/marketcore-ui-systemd-health",\n',
        '            "/marketcore-ui-systemd-health",\n'
        '            "/marketcore-ui-route-health-matrix",\n',
    )

p.write_text(s)
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

if "MarketcoreUiRouteHealthMatrixPage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.marketcore_ui_route_health_matrix import MarketcoreUiRouteHealthMatrixPage\n",
    )

if "MarketcoreUiRouteHealthMatrixPage()," not in s:
    if "MarketcoreUiSystemdHealthPage()," in s:
        s = s.replace(
            "MarketcoreUiSystemdHealthPage(),",
            "MarketcoreUiSystemdHealthPage(),\n    MarketcoreUiRouteHealthMatrixPage(),",
        )
    else:
        s = s.replace(
            "HomePage(),",
            "HomePage(),\n    MarketcoreUiRouteHealthMatrixPage(),",
        )

p.write_text(s)
PY

cat > scripts/test_marketcore_ui_8080_route_health_matrix_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_V1 ==="

scripts/apply_marketcore_ui_route_health_matrix_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_marketcore_ui_8080_route_health_matrix_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/marketcore_ui_route_health_matrix.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/marketcore_ui_route_health_matrix.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service

sleep 2

DATABASE_URL=postgresql:///finam_core MARKETCORE_UI_BASE_URL=http://127.0.0.1:8080 PYTHONPATH=src \
python src/scripts/build_marketcore_ui_8080_route_health_matrix_v1.py \
  | tee /tmp/marketcore_ui_route_health_matrix_builder_v1.txt

grep -q "VERDICT=MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_V1_READY" \
  /tmp/marketcore_ui_route_health_matrix_builder_v1.txt

curl -fsS "http://127.0.0.1:8095/api/kg/v1/marketcore-ui-route-health-matrix" \
  > /tmp/marketcore_ui_route_health_matrix_api_v1.json

curl -fsS "http://127.0.0.1:8080/marketcore-ui-route-health-matrix" \
  > /tmp/marketcore_ui_route_health_matrix_page_v1.html

grep -q '"status": "OK"' /tmp/marketcore_ui_route_health_matrix_api_v1.json
grep -q '"route"' /tmp/marketcore_ui_route_health_matrix_api_v1.json
grep -q '"http_ok"' /tmp/marketcore_ui_route_health_matrix_api_v1.json
grep -q '"content_length"' /tmp/marketcore_ui_route_health_matrix_api_v1.json

grep -q "Матрица здоровья маршрутов UI" /tmp/marketcore_ui_route_health_matrix_page_v1.html
grep -q "Маршруты" /tmp/marketcore_ui_route_health_matrix_page_v1.html
grep -q "PAPER_EDGE_DISCOVERY_MARKET_DATA_BINDING_V1" /tmp/marketcore_ui_route_health_matrix_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/marketcore_ui_route_health_matrix_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.marketcore_ui_route_health_matrix_v1;")
bad=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.marketcore_ui_route_health_matrix_v1 WHERE http_ok=false;")
home_ok=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.marketcore_ui_route_health_matrix_v1 WHERE route='/' AND http_ok=true;")
risk_ok=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.marketcore_ui_route_health_matrix_v1 WHERE route='/risk' AND http_ok=true;")
settings_ok=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.marketcore_ui_route_health_matrix_v1 WHERE route='/settings' AND http_ok=true;")

test "$rows" -gt 0
test "$home_ok" = "1"
test "$risk_ok" = "1"
test "$settings_ok" = "1"

psql -d finam_core -c "
SELECT
    group_title_ru,
    route,
    label_ru,
    http_status,
    http_ok,
    content_length,
    issue
FROM marketcore_ui.marketcore_ui_route_health_matrix_v1
ORDER BY group_key, menu_order, route;
"

echo "route_health_rows=$rows"
echo "route_health_bad_rows=$bad"
echo "home_ok=$home_ok"
echo "risk_ok=$risk_ok"
echo "settings_ok=$settings_ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_V1_OK"
SH_TEST

chmod +x scripts/test_marketcore_ui_8080_route_health_matrix_v1.sh

scripts/test_marketcore_ui_8080_route_health_matrix_v1.sh

echo "VERDICT=BUILD_MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_V1_OK"
