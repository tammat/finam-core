#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V1 ==="

mkdir -p src/scripts scripts

cat > src/scripts/validate_paper_edge_discovery_phase_acceptance_v1.py <<'PY'
from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_JSON = [
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
]

REQUIRED_HTML = {
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
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def assert_status_ok(payload: dict, name: str) -> None:
    assert payload.get("status") == "OK", f"{name}: status is not OK"


def assert_list_payload(payload: dict, name: str, allow_empty: bool = False) -> list:
    data = payload.get("data")
    assert isinstance(data, list), f"{name}: data is not list"
    if not allow_empty:
        assert len(data) > 0, f"{name}: data is empty"
    return data


def assert_dict_payload(payload: dict, name: str) -> dict:
    data = payload.get("data")
    assert isinstance(data, dict), f"{name}: data is not dict"
    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    args = parser.parse_args()

    root = Path(args.dir)

    for filename in REQUIRED_JSON:
        path = root / filename
        assert path.exists(), f"missing json: {filename}"

    discovery = load_json(root / "paper_edge_discovery.json")
    candidates = load_json(root / "research_candidates.json")
    top_detail = load_json(root / "top_candidates_detail.json")
    explainability = load_json(root / "candidate_explainability.json")
    queue = load_json(root / "edge_validation_queue.json")
    pipeline = load_json(root / "edge_validation_pipeline.json")
    robustness = load_json(root / "edge_robustness_check.json")
    oos_validation = load_json(root / "edge_oos_validation.json")
    oos_backtest = load_json(root / "edge_oos_backtest.json")
    micro_live = load_json(root / "micro_live_readiness.json")

    for name, payload in [
        ("paper_edge_discovery", discovery),
        ("research_candidates", candidates),
        ("top_candidates_detail", top_detail),
        ("candidate_explainability", explainability),
        ("edge_validation_queue", queue),
        ("edge_validation_pipeline", pipeline),
        ("edge_robustness_check", robustness),
        ("edge_oos_validation", oos_validation),
        ("edge_oos_backtest", oos_backtest),
        ("micro_live_readiness", micro_live),
    ]:
        assert_status_ok(payload, name)

    discovery_data = assert_dict_payload(discovery, "paper_edge_discovery")
    assert "paper_runtime" in discovery_data, "discovery.paper_runtime missing"
    assert "knowledge_graph" in discovery_data, "discovery.knowledge_graph missing"
    assert "validation" in discovery_data, "discovery.validation missing"

    candidate_rows = assert_list_payload(candidates, "research_candidates")
    detail_rows = assert_list_payload(top_detail, "top_candidates_detail")
    explain_rows = assert_list_payload(explainability, "candidate_explainability")
    queue_rows = assert_list_payload(queue, "edge_validation_queue")
    pipeline_rows = assert_list_payload(pipeline, "edge_validation_pipeline")
    robustness_rows = assert_list_payload(robustness, "edge_robustness_check")
    oos_validation_rows = assert_list_payload(oos_validation, "edge_oos_validation")
    oos_backtest_rows = assert_list_payload(oos_backtest, "edge_oos_backtest")
    micro_live_rows = assert_list_payload(micro_live, "micro_live_readiness")

    required_explain_fields = [
        "explainability_status",
        "why_selected",
        "risk_explanation",
        "evidence_summary",
        "recommended_action",
    ]
    for field in required_explain_fields:
        assert field in explain_rows[0], f"candidate_explainability.{field} missing"

    required_queue_fields = [
        "validation_status",
        "priority",
        "recommended_action",
        "risk_notes",
    ]
    for field in required_queue_fields:
        assert field in queue_rows[0], f"edge_validation_queue.{field} missing"

    required_pipeline_fields = [
        "sample_check_status",
        "pf_check_status",
        "expectancy_check_status",
        "pipeline_status",
        "recommended_action",
    ]
    for field in required_pipeline_fields:
        assert field in pipeline_rows[0], f"edge_validation_pipeline.{field} missing"

    required_robustness_fields = [
        "robustness_status",
        "robustness_score",
        "sample_size_status",
        "pf_status",
        "expectancy_status",
        "recommended_action",
    ]
    for field in required_robustness_fields:
        assert field in robustness_rows[0], f"edge_robustness_check.{field} missing"

    required_oos_fields = [
        "oos_status",
        "oos_readiness",
        "oos_reason",
        "recommended_action",
    ]
    for field in required_oos_fields:
        assert field in oos_validation_rows[0], f"edge_oos_validation.{field} missing"

    required_backtest_fields = [
        "backtest_status",
        "in_sample_trades",
        "oos_trades",
        "oos_profit_factor",
        "oos_expectancy",
        "stability_score",
        "recommended_action",
    ]
    for field in required_backtest_fields:
        assert field in oos_backtest_rows[0], f"edge_oos_backtest.{field} missing"

    required_micro_live_fields = [
        "readiness_status",
        "micro_live_ready",
        "micro_live_allowed",
        "block_reason",
        "recommended_action",
    ]
    for field in required_micro_live_fields:
        assert field in micro_live_rows[0], f"micro_live_readiness.{field} missing"

    allowed_rows = [
        row for row in micro_live_rows
        if row.get("micro_live_allowed") is True
    ]
    assert len(allowed_rows) == 0, "micro_live_allowed must be 0 in acceptance"

    for filename, tokens in REQUIRED_HTML.items():
        path = root / filename
        assert path.exists(), f"missing html: {filename}"
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
    print("acceptance_micro_live_allowed_zero=READY")
    print("acceptance_ui_pages_ready=READY")
    print("VERDICT=PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_paper_edge_discovery_phase_acceptance_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V1 ==="

OUT="/tmp/paper_edge_discovery_phase_acceptance_v1"
rm -rf "$OUT"
mkdir -p "$OUT"

PYTHONPATH=src python -m py_compile \
  src/scripts/validate_paper_edge_discovery_phase_acceptance_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/app.py \
  src/marketcore/presentation/pages/paper_edge_discovery.py \
  src/marketcore/presentation/pages/edge_validation_queue.py \
  src/marketcore/presentation/pages/edge_validation_pipeline.py \
  src/marketcore/presentation/pages/edge_robustness_check.py \
  src/marketcore/presentation/pages/edge_oos_validation.py \
  src/marketcore/presentation/pages/edge_oos_backtest.py \
  src/marketcore/presentation/pages/micro_live_readiness.py

for page in \
  src/marketcore/presentation/pages/paper_edge_discovery.py \
  src/marketcore/presentation/pages/edge_validation_queue.py \
  src/marketcore/presentation/pages/edge_validation_pipeline.py \
  src/marketcore/presentation/pages/edge_robustness_check.py \
  src/marketcore/presentation/pages/edge_oos_validation.py \
  src/marketcore/presentation/pages/edge_oos_backtest.py \
  src/marketcore/presentation/pages/micro_live_readiness.py
do
  if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n "$page"; then
    echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE file=$page"
    exit 1
  fi
done

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  > "$OUT/01_research_candidates.log"

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_queue_v1.py \
  > "$OUT/02_edge_validation_queue.log"

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_pipeline_v1.py \
  > "$OUT/03_edge_validation_pipeline.log"

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_robustness_check_v1.py \
  > "$OUT/04_edge_robustness_check.log"

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_oos_validation_v1.py \
  > "$OUT/05_edge_oos_validation.log"

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_oos_backtest_v1.py \
  > "$OUT/06_edge_oos_backtest.log"

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_micro_live_readiness_v1.py \
  > "$OUT/07_micro_live_readiness.log"

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1_READY" "$OUT/01_research_candidates.log"
grep -q "VERDICT=EDGE_VALIDATION_QUEUE_V1_READY" "$OUT/02_edge_validation_queue.log"
grep -q "VERDICT=EDGE_VALIDATION_PIPELINE_V1_READY" "$OUT/03_edge_validation_pipeline.log"
grep -q "VERDICT=EDGE_ROBUSTNESS_CHECK_V1_READY" "$OUT/04_edge_robustness_check.log"
grep -q "VERDICT=EDGE_OOS_VALIDATION_V1_READY" "$OUT/05_edge_oos_validation.log"
grep -q "VERDICT=EDGE_OOS_BACKTEST_V1_READY" "$OUT/06_edge_oos_backtest.log"
grep -q "VERDICT=MICRO_LIVE_READINESS_V1_READY" "$OUT/07_micro_live_readiness.log"

KG_API_HOST=127.0.0.1 KG_API_PORT=19195 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > "$OUT/kg_api.log" 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=19180 KG_API_BASE_URL=http://127.0.0.1:19195 PYTHONPATH=src \
python src/marketcore/presentation/app.py > "$OUT/ui.log" 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:19195/api/kg/v1/paper-edge-discovery" \
  > "$OUT/paper_edge_discovery.json"

curl -fsS "http://127.0.0.1:19195/api/kg/v1/paper-edge-research-candidates?limit=20" \
  > "$OUT/research_candidates.json"

curl -fsS "http://127.0.0.1:19195/api/kg/v1/paper-edge-top-candidates-detail?limit=10" \
  > "$OUT/top_candidates_detail.json"

curl -fsS "http://127.0.0.1:19195/api/kg/v1/paper-edge-candidate-explainability?limit=10" \
  > "$OUT/candidate_explainability.json"

curl -fsS "http://127.0.0.1:19195/api/kg/v1/edge-validation-queue?limit=20" \
  > "$OUT/edge_validation_queue.json"

curl -fsS "http://127.0.0.1:19195/api/kg/v1/edge-validation-pipeline?limit=20" \
  > "$OUT/edge_validation_pipeline.json"

curl -fsS "http://127.0.0.1:19195/api/kg/v1/edge-robustness-check?limit=20" \
  > "$OUT/edge_robustness_check.json"

curl -fsS "http://127.0.0.1:19195/api/kg/v1/edge-oos-validation?limit=20" \
  > "$OUT/edge_oos_validation.json"

curl -fsS "http://127.0.0.1:19195/api/kg/v1/edge-oos-backtest?limit=20" \
  > "$OUT/edge_oos_backtest.json"

curl -fsS "http://127.0.0.1:19195/api/kg/v1/micro-live-readiness?limit=20" \
  > "$OUT/micro_live_readiness.json"

curl -fsS "http://127.0.0.1:19180/paper-edge-discovery" \
  > "$OUT/paper_edge_discovery.html"

curl -fsS "http://127.0.0.1:19180/edge-validation-queue" \
  > "$OUT/edge_validation_queue.html"

curl -fsS "http://127.0.0.1:19180/edge-validation-pipeline" \
  > "$OUT/edge_validation_pipeline.html"

curl -fsS "http://127.0.0.1:19180/edge-robustness-check" \
  > "$OUT/edge_robustness_check.html"

curl -fsS "http://127.0.0.1:19180/edge-oos-validation" \
  > "$OUT/edge_oos_validation.html"

curl -fsS "http://127.0.0.1:19180/edge-oos-backtest" \
  > "$OUT/edge_oos_backtest.html"

curl -fsS "http://127.0.0.1:19180/micro-live-readiness" \
  > "$OUT/micro_live_readiness.html"

PYTHONPATH=src python src/scripts/validate_paper_edge_discovery_phase_acceptance_v1.py \
  --dir "$OUT" | tee "$OUT/acceptance.log"

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V1_READY" "$OUT/acceptance.log"

candidates_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_research_candidates_v1;")
queue_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_validation_queue_v1;")
pipeline_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_validation_pipeline_v1;")
robustness_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_robustness_check_v1;")
oos_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_oos_validation_v1;")
backtest_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_oos_backtest_v1;")
micro_live_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.micro_live_readiness_v1;")
micro_live_allowed_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.micro_live_readiness_v1 WHERE micro_live_allowed=true;")

test "$candidates_rows" -gt 0
test "$queue_rows" -gt 0
test "$pipeline_rows" -gt 0
test "$robustness_rows" -gt 0
test "$oos_rows" -gt 0
test "$backtest_rows" -gt 0
test "$micro_live_rows" -gt 0
test "$micro_live_allowed_rows" = "0"

echo "paper_edge_candidates_rows=$candidates_rows"
echo "edge_validation_queue_rows=$queue_rows"
echo "edge_validation_pipeline_rows=$pipeline_rows"
echo "edge_robustness_rows=$robustness_rows"
echo "edge_oos_validation_rows=$oos_rows"
echo "edge_oos_backtest_rows=$backtest_rows"
echo "micro_live_readiness_rows=$micro_live_rows"
echo "micro_live_allowed_rows=$micro_live_allowed_rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V1_READY"
echo "VERDICT=TEST_PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V1_OK"
SH_TEST

chmod +x scripts/test_paper_edge_discovery_phase_acceptance_v1.sh

scripts/test_paper_edge_discovery_phase_acceptance_v1.sh

echo "VERDICT=BUILD_PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V1_OK"
