#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_OOS_BACKTEST_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts src/marketcore/presentation/pages

cat > sql/marketcore_ui/016_edge_oos_backtest_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.edge_oos_backtest_v1 (
    backtest_rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',

    robustness_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    oos_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    oos_readiness TEXT NOT NULL DEFAULT 'UNKNOWN',
    backtest_status TEXT NOT NULL DEFAULT 'UNKNOWN',

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
    micro_live_candidate BOOLEAN NOT NULL DEFAULT false,

    pass_reason TEXT NOT NULL DEFAULT '',
    fail_reason TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',

    source_oos_rank INTEGER,
    source_version TEXT NOT NULL DEFAULT 'EDGE_OOS_BACKTEST_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.edge_oos_backtest_v1 TO alex;

COMMIT;

SELECT 'EDGE_OOS_BACKTEST_SCHEMA_V1_READY' AS verdict;
SQL

cat > scripts/apply_edge_oos_backtest_v1.sh <<'SH_APPLY'
#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql \
  -v ON_ERROR_STOP=1 \
  -d finam_core \
  -f sql/marketcore_ui/016_edge_oos_backtest_v1.sql
SH_APPLY

chmod +x scripts/apply_edge_oos_backtest_v1.sh

cat > src/scripts/build_edge_oos_backtest_v1.py <<'PY'
from __future__ import annotations

import os
import uuid
from statistics import mean

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "EDGE_OOS_BACKTEST_V1"


def profit_factor(values: list[float]) -> float:
    pos = sum(v for v in values if v > 0)
    neg = abs(sum(v for v in values if v < 0))

    if neg == 0 and pos > 0:
        return 999.0
    if neg == 0:
        return 0.0
    return pos / neg


def winrate(values: list[float]) -> float:
    if not values:
        return 0.0
    wins = sum(1 for v in values if v > 0)
    return wins / len(values)


def pnl(values: list[float]) -> float:
    return sum(values) if values else 0.0


def expectancy(values: list[float]) -> float:
    return mean(values) if values else 0.0


def metrics(values: list[float]) -> dict:
    return {
        "trades": len(values),
        "pnl": pnl(values),
        "expectancy": expectancy(values),
        "profit_factor": profit_factor(values),
        "winrate": winrate(values),
    }


def classify(row: dict, is_metrics: dict, oos_metrics: dict) -> dict:
    total_trades = is_metrics["trades"] + oos_metrics["trades"]
    oos_status = str(row.get("oos_status") or "UNKNOWN")
    oos_readiness = str(row.get("oos_readiness") or "UNKNOWN")

    score = 0.0
    if oos_metrics["trades"] >= 10:
        score += 0.20
    if oos_metrics["expectancy"] > 0:
        score += 0.30
    if oos_metrics["profit_factor"] >= 1.0:
        score += 0.25
    if oos_metrics["winrate"] >= 0.45:
        score += 0.15
    if is_metrics["expectancy"] > 0:
        score += 0.10

    if total_trades < 30:
        return {
            "backtest_status": "WAIT_SAMPLE",
            "stability_score": score,
            "micro_live_candidate": False,
            "pass_reason": "",
            "fail_reason": "Недостаточная общая выборка для OOS backtest.",
            "recommended_action": "Накопить выборку Paper Runtime.",
        }

    if oos_metrics["trades"] < 10:
        return {
            "backtest_status": "WAIT_OOS_SAMPLE",
            "stability_score": score,
            "micro_live_candidate": False,
            "pass_reason": "",
            "fail_reason": "Недостаточная OOS-выборка.",
            "recommended_action": "Продолжить накопление свежих OOS-сделок.",
        }

    if oos_status != "READY_FOR_OOS" and oos_readiness != "READY":
        return {
            "backtest_status": "NOT_READY_FROM_OOS_GATE",
            "stability_score": score,
            "micro_live_candidate": False,
            "pass_reason": "",
            "fail_reason": "Кандидат не получил статус READY_FOR_OOS.",
            "recommended_action": "Вернуть в robustness/OOS preparation.",
        }

    if oos_metrics["expectancy"] > 0 and oos_metrics["profit_factor"] >= 1.0 and score >= 0.70:
        return {
            "backtest_status": "OOS_PASS",
            "stability_score": score,
            "micro_live_candidate": False,
            "pass_reason": "OOS expectancy положительное, PF >= 1.0, stability score достаточный.",
            "fail_reason": "",
            "recommended_action": "Передать в MICRO_LIVE_READINESS_V1 после финальной риск-проверки.",
        }

    return {
        "backtest_status": "OOS_FAIL",
        "stability_score": score,
        "micro_live_candidate": False,
        "pass_reason": "",
        "fail_reason": "OOS-метрики не подтверждают устойчивость edge.",
        "recommended_action": "Не продвигать кандидата без дополнительного анализа.",
    }


def load_trade_pnl(cur, symbol: str, strategy: str, timeframe: str) -> list[float]:
    cur.execute(
        """
        SELECT
            COALESCE(closed_at, exit_ts, created_at) AS ts,
            net_pnl
        FROM public.closed_trades
        WHERE trade_source='paper'
          AND (%s = '' OR symbol=%s)
          AND (%s = '' OR strategy=%s)
          AND (%s = '' OR timeframe=%s)
          AND net_pnl IS NOT NULL
        ORDER BY COALESCE(closed_at, exit_ts, created_at) ASC NULLS LAST;
        """,
        (symbol, symbol, strategy, strategy, timeframe, timeframe),
    )
    rows = cur.fetchall()
    return [float(row["net_pnl"]) for row in rows if row["net_pnl"] is not None]


def split_is_oos(values: list[float]) -> tuple[list[float], list[float]]:
    if len(values) <= 1:
        return values, []
    split_at = max(1, int(len(values) * 0.70))
    return values[:split_at], values[split_at:]


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== EDGE_OOS_BACKTEST_V1 ===")

            cur.execute(
                """
                SELECT
                    oos_rank,
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    robustness_status,
                    oos_status,
                    oos_readiness
                FROM marketcore_ui.edge_oos_validation_v1
                ORDER BY
                    CASE
                        WHEN oos_status='READY_FOR_OOS' THEN 1
                        WHEN oos_status='OBSERVE_MORE' THEN 2
                        WHEN oos_status='WAIT_SAMPLE' THEN 3
                        ELSE 4
                    END,
                    oos_rank;
                """
            )
            rows = [dict(row) for row in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.edge_oos_backtest_v1;")

            for idx, row in enumerate(rows, start=1):
                symbol = str(row.get("symbol") or "")
                strategy = str(row.get("strategy") or "")
                timeframe = str(row.get("timeframe") or "")
                side = str(row.get("side") or "")

                values = load_trade_pnl(cur, symbol=symbol, strategy=strategy, timeframe=timeframe)
                is_values, oos_values = split_is_oos(values)

                is_m = metrics(is_values)
                oos_m = metrics(oos_values)
                c = classify(row, is_m, oos_m)

                cur.execute(
                    """
                    INSERT INTO marketcore_ui.edge_oos_backtest_v1 (
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
                        recommended_action,
                        source_oos_rank,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,now(),%s
                    );
                    """,
                    (
                        idx,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        row.get("robustness_status") or "UNKNOWN",
                        row.get("oos_status") or "UNKNOWN",
                        row.get("oos_readiness") or "UNKNOWN",
                        c["backtest_status"],
                        len(values),
                        is_m["trades"],
                        oos_m["trades"],
                        is_m["pnl"],
                        oos_m["pnl"],
                        is_m["expectancy"],
                        oos_m["expectancy"],
                        is_m["profit_factor"],
                        oos_m["profit_factor"],
                        is_m["winrate"],
                        oos_m["winrate"],
                        c["stability_score"],
                        c["micro_live_candidate"],
                        c["pass_reason"],
                        c["fail_reason"],
                        c["recommended_action"],
                        row.get("oos_rank"),
                        SOURCE_VERSION,
                        build_id,
                    ),
                )

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.edge_oos_backtest_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute(
                """
                SELECT backtest_status, count(*) AS rows
                FROM marketcore_ui.edge_oos_backtest_v1
                GROUP BY backtest_status
                ORDER BY backtest_status;
                """
            )
            status_rows = cur.fetchall()

    print(f"rows_written={rows_written}")
    for row in status_rows:
        print(f"backtest_status_{row['backtest_status']}={row['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_OOS_BACKTEST_V1_READY")


if __name__ == "__main__":
    main()
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/edge-oos-backtest' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/edge-oos-backtest":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
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
                        recommended_action,
                        source_oos_rank,
                        refreshed_at
                    FROM marketcore_ui.edge_oos_backtest_v1
                    ORDER BY backtest_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.edge_oos_backtest_v1",
                    "ui_direct_sql": 0,
                    "logic": "edge_oos_backtest_v1"
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > src/marketcore/presentation/pages/edge_oos_backtest.py <<'PY'
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
        return "<p>OOS Backtest пуст.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("backtest_rank", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("timeframe", "")))}</td>
            <td>{escape(str(row.get("backtest_status", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("total_trades"), 0))}</td>
            <td>{escape(ctx.formatter.number(row.get("in_sample_trades"), 0))}</td>
            <td>{escape(ctx.formatter.number(row.get("oos_trades"), 0))}</td>
            <td>{escape(ctx.formatter.number(row.get("in_sample_profit_factor"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("oos_profit_factor"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("in_sample_expectancy"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("oos_expectancy"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("stability_score"), 4))}</td>
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
                <th>Backtest</th>
                <th>Total</th>
                <th>IS</th>
                <th>OOS</th>
                <th>IS PF</th>
                <th>OOS PF</th>
                <th>IS Exp.</th>
                <th>OOS Exp.</th>
                <th>Stability</th>
                <th>Действие</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class EdgeOosBacktestPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/edge-oos-backtest",
            title="Edge OOS Backtest",
            icon="✓",
            menu_order=20,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/edge-oos-backtest?limit=50")
        rows = payload.get("data") or []

        passed = sum(1 for row in rows if row.get("backtest_status") == "OOS_PASS")
        wait = sum(1 for row in rows if str(row.get("backtest_status", "")).startswith("WAIT"))
        failed = sum(1 for row in rows if row.get("backtest_status") == "OOS_FAIL")
        not_ready = sum(1 for row in rows if row.get("backtest_status") == "NOT_READY_FROM_OOS_GATE")

        return f"""
        <section class="card">
            <h2>Edge OOS Backtest</h2>
            <p>Temporal split validation: in-sample 70% и OOS 30% по закрытым paper-сделкам.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.edge_oos_backtest_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Всего", ctx.formatter.number(len(rows), 0))}
            {_metric("OOS Pass", ctx.formatter.number(passed, 0))}
            {_metric("Wait", ctx.formatter.number(wait, 0))}
            {_metric("Not Ready", ctx.formatter.number(not_ready, 0))}
            {_metric("Failed", ctx.formatter.number(failed, 0))}
        </div>

        <section class="card">
            <h2>OOS Backtest</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>MICRO_LIVE_READINESS_V1</p>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

if "EdgeOosBacktestPage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.edge_oos_backtest import EdgeOosBacktestPage\n",
    )

if "EdgeOosBacktestPage()," not in s:
    if "EdgeOosValidationPage()," in s:
        s = s.replace(
            "EdgeOosValidationPage(),",
            "EdgeOosValidationPage(),\n    EdgeOosBacktestPage(),",
        )
    else:
        s = s.replace(
            "HomePage(),",
            "HomePage(),\n    EdgeOosBacktestPage(),",
        )

p.write_text(s)
PY

cat > scripts/test_edge_oos_backtest_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_OOS_BACKTEST_V1 ==="

scripts/apply_edge_oos_backtest_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_oos_backtest_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/edge_oos_backtest.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/edge_oos_backtest.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  > /tmp/edge_oos_backtest_candidates_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_queue_v1.py \
  > /tmp/edge_oos_backtest_queue_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_pipeline_v1.py \
  > /tmp/edge_oos_backtest_pipeline_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_robustness_check_v1.py \
  > /tmp/edge_oos_backtest_robustness_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_oos_validation_v1.py \
  > /tmp/edge_oos_backtest_oos_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_oos_backtest_v1.py \
  | tee /tmp/edge_oos_backtest_builder_v1.txt

grep -q "VERDICT=EDGE_OOS_BACKTEST_V1_READY" /tmp/edge_oos_backtest_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=18995 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_edge_oos_backtest_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=18980 KG_API_BASE_URL=http://127.0.0.1:18995 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/edge_oos_backtest_page_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:18995/api/kg/v1/edge-oos-backtest?limit=20" \
  > /tmp/edge_oos_backtest_api_v1.json

curl -fsS "http://127.0.0.1:18980/edge-oos-backtest" \
  > /tmp/edge_oos_backtest_page_v1.html

grep -q '"status": "OK"' /tmp/edge_oos_backtest_api_v1.json
grep -q '"backtest_status"' /tmp/edge_oos_backtest_api_v1.json
grep -q '"oos_profit_factor"' /tmp/edge_oos_backtest_api_v1.json
grep -q '"stability_score"' /tmp/edge_oos_backtest_api_v1.json
grep -q '"recommended_action"' /tmp/edge_oos_backtest_api_v1.json

grep -q "Edge OOS Backtest" /tmp/edge_oos_backtest_page_v1.html
grep -q "OOS Backtest" /tmp/edge_oos_backtest_page_v1.html
grep -q "MICRO_LIVE_READINESS_V1" /tmp/edge_oos_backtest_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/edge_oos_backtest_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_oos_backtest_v1;")
test "$rows" -gt 0

echo "edge_oos_backtest_rows=$rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_OOS_BACKTEST_V1_READY"
echo "VERDICT=TEST_EDGE_OOS_BACKTEST_V1_OK"
SH_TEST

chmod +x scripts/test_edge_oos_backtest_v1.sh

scripts/test_edge_oos_backtest_v1.sh

echo "VERDICT=BUILD_EDGE_OOS_BACKTEST_V1_OK"
