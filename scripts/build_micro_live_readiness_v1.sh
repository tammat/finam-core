#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_MICRO_LIVE_READINESS_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts src/marketcore/presentation/pages

cat > sql/marketcore_ui/017_micro_live_readiness_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.micro_live_readiness_v1 (
    readiness_rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',

    backtest_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    oos_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    robustness_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    readiness_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    micro_live_ready BOOLEAN NOT NULL DEFAULT false,
    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,

    total_trades INTEGER NOT NULL DEFAULT 0,
    in_sample_trades INTEGER NOT NULL DEFAULT 0,
    oos_trades INTEGER NOT NULL DEFAULT 0,

    in_sample_pnl NUMERIC(20,6),
    oos_pnl NUMERIC(20,6),
    in_sample_expectancy NUMERIC(20,6),
    oos_expectancy NUMERIC(20,6),
    in_sample_profit_factor NUMERIC(20,6),
    oos_profit_factor NUMERIC(20,6),
    in_sample_winrate NUMERIC(20,6),
    oos_winrate NUMERIC(20,6),
    stability_score NUMERIC(20,6) NOT NULL DEFAULT 0,

    block_reason TEXT NOT NULL DEFAULT '',
    evidence_summary TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',

    source_backtest_rank INTEGER,
    source_version TEXT NOT NULL DEFAULT 'MICRO_LIVE_READINESS_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.micro_live_readiness_v1 TO alex;

COMMIT;

SELECT 'MICRO_LIVE_READINESS_SCHEMA_V1_READY' AS verdict;
SQL

cat > scripts/apply_micro_live_readiness_v1.sh <<'SH_APPLY'
#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql \
  -v ON_ERROR_STOP=1 \
  -d finam_core \
  -f sql/marketcore_ui/017_micro_live_readiness_v1.sql
SH_APPLY

chmod +x scripts/apply_micro_live_readiness_v1.sh

cat > src/scripts/build_micro_live_readiness_v1.py <<'PY'
from __future__ import annotations

import os
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "MICRO_LIVE_READINESS_V1"


def dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def classify(row: dict) -> dict:
    backtest_status = str(row.get("backtest_status") or "UNKNOWN")
    oos_status = str(row.get("oos_status") or "UNKNOWN")
    robustness_status = str(row.get("robustness_status") or "UNKNOWN")

    total_trades = int(row.get("total_trades") or 0)
    oos_trades = int(row.get("oos_trades") or 0)
    oos_pf = dec(row.get("oos_profit_factor"))
    oos_exp = dec(row.get("oos_expectancy"))
    stability = dec(row.get("stability_score"))

    if total_trades < 30:
        return {
            "readiness_status": "WAIT_SAMPLE",
            "micro_live_ready": False,
            "micro_live_allowed": False,
            "block_reason": "Недостаточная общая выборка. Требуется минимум 30 paper-сделок.",
            "recommended_action": "Продолжить Paper Runtime и накопить выборку.",
        }

    if oos_trades < 10:
        return {
            "readiness_status": "WAIT_OOS_SAMPLE",
            "micro_live_ready": False,
            "micro_live_allowed": False,
            "block_reason": "Недостаточная OOS-выборка. Требуется минимум 10 OOS-сделок.",
            "recommended_action": "Продолжить OOS-наблюдение.",
        }

    if robustness_status not in {"ROBUSTNESS_REQUIRED", "WATCHLIST"}:
        return {
            "readiness_status": "BLOCKED_ROBUSTNESS",
            "micro_live_ready": False,
            "micro_live_allowed": False,
            "block_reason": "Robustness-фильтр не допускает кандидата к Micro Live.",
            "recommended_action": "Вернуть кандидата на этап robustness или отклонить.",
        }

    if oos_status != "READY_FOR_OOS":
        return {
            "readiness_status": "BLOCKED_OOS",
            "micro_live_ready": False,
            "micro_live_allowed": False,
            "block_reason": "Кандидат не получил статус READY_FOR_OOS.",
            "recommended_action": "Завершить OOS validation.",
        }

    if backtest_status != "OOS_PASS":
        return {
            "readiness_status": "BLOCKED_BACKTEST",
            "micro_live_ready": False,
            "micro_live_allowed": False,
            "block_reason": "OOS backtest не подтвердил устойчивость edge.",
            "recommended_action": "Не переводить в Micro Live.",
        }

    if oos_exp <= Decimal("0") or oos_pf < Decimal("1.0") or stability < Decimal("0.70"):
        return {
            "readiness_status": "BLOCKED_METRICS",
            "micro_live_ready": False,
            "micro_live_allowed": False,
            "block_reason": "Метрики OOS недостаточны для Micro Live.",
            "recommended_action": "Продолжить исследование или отклонить кандидата.",
        }

    return {
        "readiness_status": "READY_FOR_RISK_REVIEW",
        "micro_live_ready": True,
        "micro_live_allowed": False,
        "block_reason": "Торговое преимущество прошло статистические фильтры, но требуется финальная risk approval.",
        "recommended_action": "Передать в MICRO_LIVE_RISK_APPROVAL_V1. Автоматическое включение запрещено.",
    }


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== MICRO_LIVE_READINESS_V1 ===")

            cur.execute("""
                SELECT
                    backtest_rank,
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    robustness_status,
                    oos_status,
                    oos_readiness,
                    backtest_status,
                    total_trades,
                    in_sample_trades,
                    oos_trades,
                    in_sample_pnl,
                    oos_pnl,
                    in_sample_expectancy,
                    oos_expectancy,
                    in_sample_profit_factor,
                    oos_profit_factor,
                    in_sample_winrate,
                    oos_winrate,
                    stability_score,
                    micro_live_candidate,
                    pass_reason,
                    fail_reason,
                    recommended_action
                FROM marketcore_ui.edge_oos_backtest_v1
                ORDER BY
                    CASE
                        WHEN backtest_status='OOS_PASS' THEN 1
                        WHEN backtest_status='WAIT_OOS_SAMPLE' THEN 2
                        WHEN backtest_status='WAIT_SAMPLE' THEN 3
                        ELSE 4
                    END,
                    backtest_rank;
            """)
            rows = [dict(row) for row in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.micro_live_readiness_v1;")

            for idx, row in enumerate(rows, start=1):
                c = classify(row)

                evidence_summary = (
                    f"Backtest={row.get('backtest_status') or 'UNKNOWN'}; "
                    f"OOS={row.get('oos_status') or 'UNKNOWN'}; "
                    f"Robustness={row.get('robustness_status') or 'UNKNOWN'}; "
                    f"TotalTrades={row.get('total_trades') or 0}; "
                    f"OOSTrades={row.get('oos_trades') or 0}; "
                    f"OOSPF={row.get('oos_profit_factor') or 0}; "
                    f"OOSExpectancy={row.get('oos_expectancy') or 0}; "
                    f"Stability={row.get('stability_score') or 0}"
                )

                cur.execute("""
                    INSERT INTO marketcore_ui.micro_live_readiness_v1 (
                        readiness_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        backtest_status,
                        oos_status,
                        robustness_status,
                        readiness_status,
                        micro_live_ready,
                        micro_live_allowed,
                        total_trades,
                        in_sample_trades,
                        oos_trades,
                        in_sample_pnl,
                        oos_pnl,
                        in_sample_expectancy,
                        oos_expectancy,
                        in_sample_profit_factor,
                        oos_profit_factor,
                        in_sample_winrate,
                        oos_winrate,
                        stability_score,
                        block_reason,
                        evidence_summary,
                        recommended_action,
                        source_backtest_rank,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,now(),%s
                    );
                """, (
                    idx,
                    row.get("symbol") or "",
                    row.get("strategy") or "",
                    row.get("timeframe") or "",
                    row.get("side") or "",
                    row.get("backtest_status") or "UNKNOWN",
                    row.get("oos_status") or "UNKNOWN",
                    row.get("robustness_status") or "UNKNOWN",
                    c["readiness_status"],
                    c["micro_live_ready"],
                    c["micro_live_allowed"],
                    row.get("total_trades") or 0,
                    row.get("in_sample_trades") or 0,
                    row.get("oos_trades") or 0,
                    row.get("in_sample_pnl"),
                    row.get("oos_pnl"),
                    row.get("in_sample_expectancy"),
                    row.get("oos_expectancy"),
                    row.get("in_sample_profit_factor"),
                    row.get("oos_profit_factor"),
                    row.get("in_sample_winrate"),
                    row.get("oos_winrate"),
                    row.get("stability_score") or 0,
                    c["block_reason"],
                    evidence_summary,
                    c["recommended_action"],
                    row.get("backtest_rank"),
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.micro_live_readiness_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT readiness_status, count(*) AS rows
                FROM marketcore_ui.micro_live_readiness_v1
                GROUP BY readiness_status
                ORDER BY readiness_status;
            """)
            status_rows = cur.fetchall()

            cur.execute("""
                SELECT count(*) AS ready
                FROM marketcore_ui.micro_live_readiness_v1
                WHERE micro_live_ready=true;
            """)
            ready_rows = int(cur.fetchone()["ready"])

            cur.execute("""
                SELECT count(*) AS allowed
                FROM marketcore_ui.micro_live_readiness_v1
                WHERE micro_live_allowed=true;
            """)
            allowed_rows = int(cur.fetchone()["allowed"])

    print(f"rows_written={rows_written}")
    print(f"micro_live_ready_rows={ready_rows}")
    print(f"micro_live_allowed_rows={allowed_rows}")
    for row in status_rows:
        print(f"readiness_status_{row['readiness_status']}={row['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MICRO_LIVE_READINESS_V1_READY")


if __name__ == "__main__":
    main()
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/micro-live-readiness' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/micro-live-readiness":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
                    SELECT
                        readiness_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        backtest_status,
                        oos_status,
                        robustness_status,
                        readiness_status,
                        micro_live_ready,
                        micro_live_allowed,
                        total_trades,
                        in_sample_trades,
                        oos_trades,
                        in_sample_pnl,
                        oos_pnl,
                        in_sample_expectancy,
                        oos_expectancy,
                        in_sample_profit_factor,
                        oos_profit_factor,
                        in_sample_winrate,
                        oos_winrate,
                        stability_score,
                        block_reason,
                        evidence_summary,
                        recommended_action,
                        source_backtest_rank,
                        refreshed_at
                    FROM marketcore_ui.micro_live_readiness_v1
                    ORDER BY readiness_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.micro_live_readiness_v1",
                    "ui_direct_sql": 0,
                    "logic": "micro_live_readiness_v1",
                    "orders_changed": 0,
                    "execution_changed": 0
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > src/marketcore/presentation/pages/micro_live_readiness.py <<'PY'
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
        return "<p>Micro Live Readiness пуст.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("readiness_rank", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("timeframe", "")))}</td>
            <td>{escape(str(row.get("readiness_status", "")))}</td>
            <td>{escape(str(row.get("micro_live_ready", "")))}</td>
            <td>{escape(str(row.get("micro_live_allowed", "")))}</td>
            <td>{escape(str(row.get("backtest_status", "")))}</td>
            <td>{escape(str(row.get("oos_status", "")))}</td>
            <td>{escape(str(row.get("robustness_status", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("total_trades"), 0))}</td>
            <td>{escape(ctx.formatter.number(row.get("oos_trades"), 0))}</td>
            <td>{escape(ctx.formatter.number(row.get("oos_profit_factor"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("oos_expectancy"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("stability_score"), 4))}</td>
            <td>{escape(str(row.get("block_reason", "")))}</td>
            <td>{escape(str(row.get("recommended_action", "")))}</td>
        </tr>
        """

    return f"""
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Инструмент</th>
                <th>Стратегия</th>
                <th>TF</th>
                <th>Readiness</th>
                <th>Ready</th>
                <th>Allowed</th>
                <th>Backtest</th>
                <th>OOS</th>
                <th>Robustness</th>
                <th>Total</th>
                <th>OOS Trades</th>
                <th>OOS PF</th>
                <th>OOS Exp.</th>
                <th>Stability</th>
                <th>Block Reason</th>
                <th>Action</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class MicroLiveReadinessPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/micro-live-readiness",
            title="Micro Live Readiness",
            icon="▶",
            menu_order=21,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/micro-live-readiness?limit=50")
        rows = payload.get("data") or []

        ready = sum(1 for row in rows if row.get("micro_live_ready") is True)
        allowed = sum(1 for row in rows if row.get("micro_live_allowed") is True)
        wait_sample = sum(1 for row in rows if row.get("readiness_status") in {"WAIT_SAMPLE", "WAIT_OOS_SAMPLE"})
        blocked = sum(1 for row in rows if str(row.get("readiness_status", "")).startswith("BLOCKED"))

        return f"""
        <section class="card">
            <h2>Micro Live Readiness</h2>
            <p>Финальный шлюз допуска кандидата к Micro Live. Автоматическое включение исполнения запрещено.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.micro_live_readiness_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Всего", ctx.formatter.number(len(rows), 0))}
            {_metric("Ready", ctx.formatter.number(ready, 0), "Готовы к risk review")}
            {_metric("Allowed", ctx.formatter.number(allowed, 0), "Должно быть 0")}
            {_metric("Wait Sample", ctx.formatter.number(wait_sample, 0))}
            {_metric("Blocked", ctx.formatter.number(blocked, 0))}
        </div>

        <section class="card">
            <h2>Readiness Gate</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V1</p>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

if "MicroLiveReadinessPage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.micro_live_readiness import MicroLiveReadinessPage\n",
    )

if "MicroLiveReadinessPage()," not in s:
    if "EdgeOosBacktestPage()," in s:
        s = s.replace(
            "EdgeOosBacktestPage(),",
            "EdgeOosBacktestPage(),\n    MicroLiveReadinessPage(),",
        )
    else:
        s = s.replace(
            "HomePage(),",
            "HomePage(),\n    MicroLiveReadinessPage(),",
        )

p.write_text(s)
PY

cat > scripts/test_micro_live_readiness_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MICRO_LIVE_READINESS_V1 ==="

scripts/apply_micro_live_readiness_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_micro_live_readiness_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/micro_live_readiness.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/micro_live_readiness.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  > /tmp/micro_live_candidates_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_queue_v1.py \
  > /tmp/micro_live_queue_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_pipeline_v1.py \
  > /tmp/micro_live_pipeline_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_robustness_check_v1.py \
  > /tmp/micro_live_robustness_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_oos_validation_v1.py \
  > /tmp/micro_live_oos_validation_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_oos_backtest_v1.py \
  > /tmp/micro_live_oos_backtest_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_micro_live_readiness_v1.py \
  | tee /tmp/micro_live_readiness_builder_v1.txt

grep -q "VERDICT=MICRO_LIVE_READINESS_V1_READY" /tmp/micro_live_readiness_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=19095 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_micro_live_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=19080 KG_API_BASE_URL=http://127.0.0.1:19095 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/micro_live_page_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:19095/api/kg/v1/micro-live-readiness?limit=20" \
  > /tmp/micro_live_readiness_api_v1.json

curl -fsS "http://127.0.0.1:19080/micro-live-readiness" \
  > /tmp/micro_live_readiness_page_v1.html

grep -q '"status": "OK"' /tmp/micro_live_readiness_api_v1.json
grep -q '"readiness_status"' /tmp/micro_live_readiness_api_v1.json
grep -q '"micro_live_ready"' /tmp/micro_live_readiness_api_v1.json
grep -q '"micro_live_allowed"' /tmp/micro_live_readiness_api_v1.json
grep -q '"recommended_action"' /tmp/micro_live_readiness_api_v1.json

grep -q "Micro Live Readiness" /tmp/micro_live_readiness_page_v1.html
grep -q "Readiness Gate" /tmp/micro_live_readiness_page_v1.html
grep -q "PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V1" /tmp/micro_live_readiness_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/micro_live_readiness_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.micro_live_readiness_v1;")
allowed=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.micro_live_readiness_v1 WHERE micro_live_allowed=true;")

test "$rows" -gt 0
test "$allowed" = "0"

echo "micro_live_readiness_rows=$rows"
echo "micro_live_allowed_rows=$allowed"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MICRO_LIVE_READINESS_V1_READY"
echo "VERDICT=TEST_MICRO_LIVE_READINESS_V1_OK"
SH_TEST

chmod +x scripts/test_micro_live_readiness_v1.sh

scripts/test_micro_live_readiness_v1.sh

echo "VERDICT=BUILD_MICRO_LIVE_READINESS_V1_OK"
