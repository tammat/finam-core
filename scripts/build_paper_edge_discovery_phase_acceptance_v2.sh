#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V2 ==="

mkdir -p src/scripts scripts

cat > src/scripts/validate_paper_edge_discovery_phase_acceptance_v2.py <<'PY'
from __future__ import annotations

import argparse
import json
from pathlib import Path


API_FILES = [
    "paper_edge_discovery.json",
    "research_candidates.json",
    "top_candidates_detail.json",
    "candidate_explainability.json",
    "edge_validation_queue.json",
    "edge_validation_pipeline.json",
    "edge_robustness_check.json",
    "edge_oos_validation.json",
    "edge_oos_backtest.json",
    "micro_live_readiness.json",
    "paper_sample_accumulation_monitor.json",
]

HTML_TOKENS = {
    "paper_edge_discovery.html": [
        "Центр поиска Edge",
        "Candidate Explainability",
        "TOP Candidates Detail",
        "Research Candidates",
        "Paper Runtime Real Data",
        "MARKETCORE_UI_SHELL_V1",
    ],
    "edge_validation_queue.html": [
        "Edge Validation Queue",
        "EDGE_VALIDATION_PIPELINE_V1",
        "MARKETCORE_UI_SHELL_V1",
    ],
    "edge_validation_pipeline.html": [
        "Edge Validation Pipeline",
        "EDGE_ROBUSTNESS_CHECK_V1",
        "MARKETCORE_UI_SHELL_V1",
    ],
    "edge_robustness_check.html": [
        "Edge Robustness Check",
        "EDGE_OOS_VALIDATION_V1",
        "MARKETCORE_UI_SHELL_V1",
    ],
    "edge_oos_validation.html": [
        "Edge OOS Validation",
        "EDGE_OOS_BACKTEST_V1",
        "MARKETCORE_UI_SHELL_V1",
    ],
    "edge_oos_backtest.html": [
        "Edge OOS Backtest",
        "MICRO_LIVE_READINESS_V1",
        "MARKETCORE_UI_SHELL_V1",
    ],
    "micro_live_readiness.html": [
        "Micro Live Readiness",
        "PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V1",
        "MARKETCORE_UI_SHELL_V1",
    ],
    "paper_sample_accumulation_monitor.html": [
        "Paper Sample Accumulation Monitor",
        "Accumulation",
        "PAPER_RUNTIME_SAMPLE_COLLECTION_V1",
        "MARKETCORE_UI_SHELL_V1",
    ],
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def must_ok(name: str, payload: dict) -> None:
    assert payload.get("status") == "OK", f"{name}: status != OK"


def must_list(name: str, payload: dict) -> list:
    data = payload.get("data")
    assert isinstance(data, list), f"{name}: data is not list"
    assert len(data) > 0, f"{name}: data is empty"
    return data


def must_dict(name: str, payload: dict) -> dict:
    data = payload.get("data")
    assert isinstance(data, dict), f"{name}: data is not dict"
    return data


def require_fields(row: dict, fields: list[str], name: str) -> None:
    for field in fields:
        assert field in row, f"{name}: missing field {field}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    args = parser.parse_args()

    root = Path(args.dir)

    payloads: dict[str, dict] = {}
    for filename in API_FILES:
        path = root / filename
        assert path.exists(), f"missing api file: {filename}"
        payload = load_json(path)
        must_ok(filename, payload)
        payloads[filename] = payload

    discovery = must_dict("paper_edge_discovery", payloads["paper_edge_discovery.json"])
    assert "paper_runtime" in discovery, "discovery.paper_runtime missing"
    assert "knowledge_graph" in discovery, "discovery.knowledge_graph missing"
    assert "validation" in discovery, "discovery.validation missing"

    candidates = must_list("research_candidates", payloads["research_candidates.json"])
    top_detail = must_list("top_candidates_detail", payloads["top_candidates_detail.json"])
    explain = must_list("candidate_explainability", payloads["candidate_explainability.json"])
    queue = must_list("edge_validation_queue", payloads["edge_validation_queue.json"])
    pipeline = must_list("edge_validation_pipeline", payloads["edge_validation_pipeline.json"])
    robustness = must_list("edge_robustness_check", payloads["edge_robustness_check.json"])
    oos_validation = must_list("edge_oos_validation", payloads["edge_oos_validation.json"])
    oos_backtest = must_list("edge_oos_backtest", payloads["edge_oos_backtest.json"])
    micro_live = must_list("micro_live_readiness", payloads["micro_live_readiness.json"])
    sample_monitor = must_list("paper_sample_accumulation_monitor", payloads["paper_sample_accumulation_monitor.json"])

    require_fields(candidates[0], ["symbol", "strategy", "candidate_status", "profit_factor", "expectancy"], "research_candidates")
    require_fields(top_detail[0], ["detail_status", "next_step"], "top_candidates_detail")
    require_fields(explain[0], ["explainability_status", "why_selected", "risk_explanation", "evidence_summary", "recommended_action"], "candidate_explainability")
    require_fields(queue[0], ["validation_status", "priority", "recommended_action", "risk_notes"], "edge_validation_queue")
    require_fields(pipeline[0], ["sample_check_status", "pf_check_status", "expectancy_check_status", "pipeline_status", "recommended_action"], "edge_validation_pipeline")
    require_fields(robustness[0], ["robustness_status", "robustness_score", "sample_size_status", "pf_status", "expectancy_status", "recommended_action"], "edge_robustness_check")
    require_fields(oos_validation[0], ["oos_status", "oos_readiness", "oos_reason", "recommended_action"], "edge_oos_validation")
    require_fields(oos_backtest[0], ["backtest_status", "oos_profit_factor", "oos_expectancy", "stability_score", "recommended_action"], "edge_oos_backtest")
    require_fields(micro_live[0], ["readiness_status", "micro_live_ready", "micro_live_allowed", "block_reason", "recommended_action"], "micro_live_readiness")
    require_fields(sample_monitor[0], ["sample_status", "remaining_total_trades", "remaining_oos_trades", "progress_pct", "recommended_action"], "paper_sample_accumulation_monitor")

    allowed_rows = [row for row in micro_live if row.get("micro_live_allowed") is True]
    assert len(allowed_rows) == 0, "micro_live_allowed must be 0"

    sample_allowed_rows = [row for row in sample_monitor if row.get("micro_live_allowed") is True]
    assert len(sample_allowed_rows) == 0, "sample_monitor.micro_live_allowed must be 0"

    sample_collection = load_json(root / "paper_runtime_sample_collection.json")
    assert isinstance(sample_collection, dict), "paper_runtime_sample_collection is not dict"
    assert sample_collection.get("micro_live_allowed") is False, "sample_collection.micro_live_allowed must be false"
    assert sample_collection.get("candidates_total", 0) > 0, "sample_collection.candidates_total must be > 0"
    assert "collection_status" in sample_collection, "sample_collection.collection_status missing"
    assert "phase_status" in sample_collection, "sample_collection.phase_status missing"

    for filename, tokens in HTML_TOKENS.items():
        path = root / filename
        assert path.exists(), f"missing html file: {filename}"
        html = path.read_text(encoding="utf-8")
        for token in tokens:
            assert token in html, f"{filename}: missing token {token}"

    print("acceptance_discovery_ready=READY")
    print("acceptance_research_candidates_ready=READY")
    print("acceptance_top_detail_ready=READY")
    print("acceptance_candidate_explainability_ready=READY")
    print("acceptance_edge_validation_queue_ready=READY")
    print("acceptance_edge_validation_pipeline_ready=READY")
    print("acceptance_robustness_ready=READY")
    print("acceptance_oos_validation_ready=READY")
    print("acceptance_oos_backtest_ready=READY")
    print("acceptance_micro_live_readiness_ready=READY")
    print("acceptance_sample_monitor_ready=READY")
    print("acceptance_sample_collection_ready=READY")
    print("acceptance_micro_live_allowed_zero=READY")
    print("acceptance_ui_pages_ready=READY")
    print("VERDICT=PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V2_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_paper_edge_discovery_phase_acceptance_v2.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V2 ==="

OUT="/tmp/paper_edge_discovery_phase_acceptance_v2"
rm -rf "$OUT"
mkdir -p "$OUT"

PYTHONPATH=src python -m py_compile \
  src/scripts/validate_paper_edge_discovery_phase_acceptance_v2.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/app.py \
  src/marketcore/presentation/pages/paper_edge_discovery.py \
  src/marketcore/presentation/pages/edge_validation_queue.py \
  src/marketcore/presentation/pages/edge_validation_pipeline.py \
  src/marketcore/presentation/pages/edge_robustness_check.py \
  src/marketcore/presentation/pages/edge_oos_validation.py \
  src/marketcore/presentation/pages/edge_oos_backtest.py \
  src/marketcore/presentation/pages/micro_live_readiness.py \
  src/marketcore/presentation/pages/paper_sample_accumulation_monitor.py

for page in \
  src/marketcore/presentation/pages/paper_edge_discovery.py \
  src/marketcore/presentation/pages/edge_validation_queue.py \
  src/marketcore/presentation/pages/edge_validation_pipeline.py \
  src/marketcore/presentation/pages/edge_robustness_check.py \
  src/marketcore/presentation/pages/edge_oos_validation.py \
  src/marketcore/presentation/pages/edge_oos_backtest.py \
  src/marketcore/presentation/pages/micro_live_readiness.py \
  src/marketcore/presentation/pages/paper_sample_accumulation_monitor.py
do
  if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n "$page"; then
    echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE file=$page"
    exit 1
  fi
done

sudo -u postgres env DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  > "$OUT/01_research_candidates.log"

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python src/scripts/build_edge_validation_queue_v1.py \
  > "$OUT/02_edge_validation_queue.log"

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python src/scripts/build_edge_validation_pipeline_v1.py \
  > "$OUT/03_edge_validation_pipeline.log"

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python src/scripts/build_edge_robustness_check_v1.py \
  > "$OUT/04_edge_robustness_check.log"

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python src/scripts/build_edge_oos_validation_v1.py \
  > "$OUT/05_edge_oos_validation.log"

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python src/scripts/build_edge_oos_backtest_v1.py \
  > "$OUT/06_edge_oos_backtest.log"

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python src/scripts/build_micro_live_readiness_v1.py \
  > "$OUT/07_micro_live_readiness.log"

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python src/scripts/build_paper_sample_accumulation_monitor_v1.py \
  > "$OUT/08_sample_monitor.log"

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python src/scripts/build_paper_runtime_sample_collection_v1.py \
  > "$OUT/09_sample_collection.log"

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1_READY" "$OUT/01_research_candidates.log"
grep -q "VERDICT=EDGE_VALIDATION_QUEUE_V1_READY" "$OUT/02_edge_validation_queue.log"
grep -q "VERDICT=EDGE_VALIDATION_PIPELINE_V1_READY" "$OUT/03_edge_validation_pipeline.log"
grep -q "VERDICT=EDGE_ROBUSTNESS_CHECK_V1_READY" "$OUT/04_edge_robustness_check.log"
grep -q "VERDICT=EDGE_OOS_VALIDATION_V1_READY" "$OUT/05_edge_oos_validation.log"
grep -q "VERDICT=EDGE_OOS_BACKTEST_V1_READY" "$OUT/06_edge_oos_backtest.log"
grep -q "VERDICT=MICRO_LIVE_READINESS_V1_READY" "$OUT/07_micro_live_readiness.log"
grep -q "VERDICT=PAPER_SAMPLE_ACCUMULATION_MONITOR_V1_READY" "$OUT/08_sample_monitor.log"
grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_V1_READY" "$OUT/09_sample_collection.log"

KG_API_HOST=127.0.0.1 KG_API_PORT=19395 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > "$OUT/kg_api.log" 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=19380 KG_API_BASE_URL=http://127.0.0.1:19395 PYTHONPATH=src \
python src/marketcore/presentation/app.py > "$OUT/ui.log" 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:19395/api/kg/v1/paper-edge-discovery" > "$OUT/paper_edge_discovery.json"
curl -fsS "http://127.0.0.1:19395/api/kg/v1/paper-edge-research-candidates?limit=20" > "$OUT/research_candidates.json"
curl -fsS "http://127.0.0.1:19395/api/kg/v1/paper-edge-top-candidates-detail?limit=10" > "$OUT/top_candidates_detail.json"
curl -fsS "http://127.0.0.1:19395/api/kg/v1/paper-edge-candidate-explainability?limit=10" > "$OUT/candidate_explainability.json"
curl -fsS "http://127.0.0.1:19395/api/kg/v1/edge-validation-queue?limit=20" > "$OUT/edge_validation_queue.json"
curl -fsS "http://127.0.0.1:19395/api/kg/v1/edge-validation-pipeline?limit=20" > "$OUT/edge_validation_pipeline.json"
curl -fsS "http://127.0.0.1:19395/api/kg/v1/edge-robustness-check?limit=20" > "$OUT/edge_robustness_check.json"
curl -fsS "http://127.0.0.1:19395/api/kg/v1/edge-oos-validation?limit=20" > "$OUT/edge_oos_validation.json"
curl -fsS "http://127.0.0.1:19395/api/kg/v1/edge-oos-backtest?limit=20" > "$OUT/edge_oos_backtest.json"
curl -fsS "http://127.0.0.1:19395/api/kg/v1/micro-live-readiness?limit=20" > "$OUT/micro_live_readiness.json"
curl -fsS "http://127.0.0.1:19395/api/kg/v1/paper-sample-accumulation-monitor?limit=20" > "$OUT/paper_sample_accumulation_monitor.json"

psql -At -d finam_core -c "
SELECT row_to_json(t)
FROM (
  SELECT *
  FROM marketcore_ui.paper_runtime_sample_collection_v1
  WHERE id=1
) t;
" > "$OUT/paper_runtime_sample_collection.json"

curl -fsS "http://127.0.0.1:19380/paper-edge-discovery" > "$OUT/paper_edge_discovery.html"
curl -fsS "http://127.0.0.1:19380/edge-validation-queue" > "$OUT/edge_validation_queue.html"
curl -fsS "http://127.0.0.1:19380/edge-validation-pipeline" > "$OUT/edge_validation_pipeline.html"
curl -fsS "http://127.0.0.1:19380/edge-robustness-check" > "$OUT/edge_robustness_check.html"
curl -fsS "http://127.0.0.1:19380/edge-oos-validation" > "$OUT/edge_oos_validation.html"
curl -fsS "http://127.0.0.1:19380/edge-oos-backtest" > "$OUT/edge_oos_backtest.html"
curl -fsS "http://127.0.0.1:19380/micro-live-readiness" > "$OUT/micro_live_readiness.html"
curl -fsS "http://127.0.0.1:19380/paper-sample-accumulation-monitor" > "$OUT/paper_sample_accumulation_monitor.html"

PYTHONPATH=src python src/scripts/validate_paper_edge_discovery_phase_acceptance_v2.py \
  --dir "$OUT" | tee "$OUT/acceptance.log"

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V2_READY" "$OUT/acceptance.log"

candidates_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_research_candidates_v1;")
queue_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_validation_queue_v1;")
pipeline_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_validation_pipeline_v1;")
robustness_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_robustness_check_v1;")
oos_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_oos_validation_v1;")
backtest_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_oos_backtest_v1;")
micro_live_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.micro_live_readiness_v1;")
sample_monitor_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_sample_accumulation_monitor_v1;")
sample_collection_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_v1 WHERE id=1;")
micro_live_allowed_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.micro_live_readiness_v1 WHERE micro_live_allowed=true;")

test "$candidates_rows" -gt 0
test "$queue_rows" -gt 0
test "$pipeline_rows" -gt 0
test "$robustness_rows" -gt 0
test "$oos_rows" -gt 0
test "$backtest_rows" -gt 0
test "$micro_live_rows" -gt 0
test "$sample_monitor_rows" -gt 0
test "$sample_collection_rows" = "1"
test "$micro_live_allowed_rows" = "0"

echo "paper_edge_candidates_rows=$candidates_rows"
echo "edge_validation_queue_rows=$queue_rows"
echo "edge_validation_pipeline_rows=$pipeline_rows"
echo "edge_robustness_rows=$robustness_rows"
echo "edge_oos_validation_rows=$oos_rows"
echo "edge_oos_backtest_rows=$backtest_rows"
echo "micro_live_readiness_rows=$micro_live_rows"
echo "sample_monitor_rows=$sample_monitor_rows"
echo "sample_collection_rows=$sample_collection_rows"
echo "micro_live_allowed_rows=$micro_live_allowed_rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V2_READY"
echo "VERDICT=TEST_PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V2_OK"
SH_TEST

chmod +x scripts/test_paper_edge_discovery_phase_acceptance_v2.sh

scripts/test_paper_edge_discovery_phase_acceptance_v2.sh

echo "VERDICT=BUILD_PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V2_OK"
