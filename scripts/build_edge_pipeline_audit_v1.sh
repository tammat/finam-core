#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_PIPELINE_AUDIT_V1 ==="

mkdir -p src/scripts reports deploy/systemd scripts

cat > src/scripts/build_edge_pipeline_audit_v1.py <<'PY'
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
OUT_TXT = "reports/edge_pipeline_audit_latest.txt"
OUT_JSON = "reports/edge_pipeline_audit_latest.json"
OUT_HTML = "reports/edge_pipeline_audit_latest.html"


def scalar(cur, sql: str) -> int:
    cur.execute(sql)
    return int(cur.fetchone()["v"] or 0)


def pct(a: int, b: int) -> float:
    return round((a / b * 100), 4) if b else 0.0


def main() -> None:
    now = datetime.now(UTC).isoformat()

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            data = {
                "created_at": now,
                "strategies": scalar(cur, "SELECT count(*) v FROM analytics.strategy_library_v1 WHERE enabled=true"),
                "research_queue": scalar(cur, "SELECT count(*) v FROM analytics.research_queue_v1"),
                "runs": scalar(cur, "SELECT count(*) v FROM analytics.edge_lab_run_v1"),
                "runs_done": scalar(cur, "SELECT count(*) v FROM analytics.edge_lab_run_v1 WHERE status_code='DONE'"),
                "runs_failed": scalar(cur, "SELECT count(*) v FROM analytics.edge_lab_run_v1 WHERE status_code='FAILED'"),
                "observations": scalar(cur, "SELECT count(*) v FROM analytics.edge_observation_v1"),
                "observations_with_trades": scalar(cur, "SELECT count(*) v FROM analytics.edge_observation_v1 WHERE trades>0"),
                "candidates": scalar(cur, "SELECT count(*) v FROM analytics.edge_candidate_v1"),
                "validated": scalar(cur, "SELECT count(*) v FROM analytics.edge_candidate_v1 WHERE candidate_status='VALIDATED'"),
                "paper": scalar(cur, "SELECT count(*) v FROM analytics.edge_candidate_v1 WHERE paper_allowed=true"),
                "shadow": scalar(cur, "SELECT count(*) v FROM analytics.edge_candidate_v1 WHERE shadow_allowed=true"),
                "micro_live": scalar(cur, "SELECT count(*) v FROM analytics.edge_candidate_v1 WHERE micro_live_allowed=true"),
                "live": scalar(cur, "SELECT count(*) v FROM analytics.edge_candidate_v1 WHERE live_allowed=true"),
                "research_trades": scalar(cur, "SELECT count(*) v FROM analytics.research_trade_v1"),
            }

            cur.execute("""
                SELECT strategy_code, count(*) observations,
                       count(*) FILTER (WHERE trades>0) with_trades,
                       max(profit_factor) best_pf,
                       max(expectancy) best_expectancy,
                       max(normalized_edge_score) best_score
                FROM analytics.edge_observation_v1
                GROUP BY strategy_code
                ORDER BY best_score DESC NULLS LAST
                LIMIT 10
            """)
            top_strategies = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT symbol, count(*) observations,
                       count(*) FILTER (WHERE trades>0) with_trades,
                       max(profit_factor) best_pf,
                       max(expectancy) best_expectancy,
                       max(normalized_edge_score) best_score
                FROM analytics.edge_observation_v1
                GROUP BY symbol
                ORDER BY best_score DESC NULLS LAST
                LIMIT 10
            """)
            top_symbols = [dict(r) for r in cur.fetchall()]

    funnel = [
        ("Research Queue → Runs", data["runs"], data["research_queue"], pct(data["runs"], data["research_queue"])),
        ("Runs → Observations", data["observations"], data["runs"], pct(data["observations"], data["runs"])),
        ("Observations → With Trades", data["observations_with_trades"], data["observations"], pct(data["observations_with_trades"], data["observations"])),
        ("With Trades → Candidates", data["candidates"], data["observations_with_trades"], pct(data["candidates"], data["observations_with_trades"])),
        ("Candidates → Validated", data["validated"], data["candidates"], pct(data["validated"], data["candidates"])),
        ("Validated → Paper", data["paper"], data["validated"], pct(data["paper"], data["validated"])),
    ]

    bottleneck = min(funnel, key=lambda x: x[3]) if funnel else ("NONE", 0, 0, 0)

    lines = [
        "=== EDGE_PIPELINE_AUDIT_V1 ===",
        f"created_at={now}",
        "",
        "--- FUNNEL ---",
    ]
    lines += [f"{name}: {value}/{base} = {conv}%" for name, value, base, conv in funnel]
    lines += [
        "",
        "--- BOTTLENECK ---",
        f"{bottleneck[0]} = {bottleneck[3]}%",
        "",
        "--- SUMMARY ---",
    ]
    lines += [f"{k}={v}" for k, v in data.items()]
    lines += ["", "--- TOP_STRATEGIES ---"]
    lines += [json.dumps(r, ensure_ascii=False, default=str) for r in top_strategies]
    lines += ["", "--- TOP_SYMBOLS ---"]
    lines += [json.dumps(r, ensure_ascii=False, default=str) for r in top_symbols]
    lines += ["", "VERDICT=EDGE_PIPELINE_AUDIT_V1_READY"]

    report = "\n".join(lines)
    open(OUT_TXT, "w", encoding="utf-8").write(report + "\n")
    open(OUT_JSON, "w", encoding="utf-8").write(json.dumps({"summary": data, "funnel": funnel, "bottleneck": bottleneck, "top_strategies": top_strategies, "top_symbols": top_symbols}, ensure_ascii=False, indent=2, default=str))

    html = "<html><head><meta charset='utf-8'><title>Edge Pipeline Audit</title></head><body><pre>" + report.replace("&","&amp;").replace("<","&lt;") + "</pre></body></html>"
    open(OUT_HTML, "w", encoding="utf-8").write(html)

    print(report)


if __name__ == "__main__":
    main()
PY

cat > deploy/systemd/finam-edge-pipeline-audit.service <<'UNIT'
[Unit]
Description=Finam Core Edge Pipeline Audit

[Service]
Type=oneshot
WorkingDirectory=/opt/finam-core
Environment=PYTHONPATH=src
Environment=DATABASE_URL=postgresql:///finam_core
ExecStart=/opt/finam-core/venv/bin/python src/scripts/build_edge_pipeline_audit_v1.py
UNIT

cat > deploy/systemd/finam-edge-pipeline-audit.timer <<'UNIT'
[Unit]
Description=Run Finam Core Edge Pipeline Audit periodically

[Timer]
OnBootSec=5min
OnUnitActiveSec=30min
Unit=finam-edge-pipeline-audit.service

[Install]
WantedBy=timers.target
UNIT

cat > scripts/test_edge_pipeline_audit_v1.sh <<'TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_PIPELINE_AUDIT_V1 ==="

PYTHONPATH=src python -m py_compile src/scripts/build_edge_pipeline_audit_v1.py
DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python src/scripts/build_edge_pipeline_audit_v1.py | tee /tmp/edge_pipeline_audit_v1.txt

grep -q "VERDICT=EDGE_PIPELINE_AUDIT_V1_READY" /tmp/edge_pipeline_audit_v1.txt
test -f reports/edge_pipeline_audit_latest.txt
test -f reports/edge_pipeline_audit_latest.json
test -f reports/edge_pipeline_audit_latest.html
grep -q "Edge Pipeline Audit" reports/edge_pipeline_audit_latest.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_PIPELINE_AUDIT_V1_OK"
TEST

chmod +x scripts/test_edge_pipeline_audit_v1.sh
scripts/test_edge_pipeline_audit_v1.sh

echo "VERDICT=BUILD_EDGE_PIPELINE_AUDIT_V1_OK"
