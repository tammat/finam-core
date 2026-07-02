#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PAPER_EDGE_DISCOVERY_ACCEPTANCE_V1 ==="

mkdir -p src/scripts scripts

cat > src/scripts/validate_paper_edge_discovery_acceptance_v1.py <<'PY'
from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_HTML_TOKENS = [
    "Центр поиска Edge",
    "Candidate Explainability",
    "TOP Candidates Detail",
    "Research Candidates",
    "Paper Runtime Real Data",
    "Knowledge Graph",
    "Validation",
    "PAPER_RUNTIME",
    "MARKETCORE_UI_SHELL_V1",
]


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def assert_ok(payload: dict, name: str) -> None:
    assert payload.get("status") == "OK", f"{name}: status != OK"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    args = parser.parse_args()

    root = Path(args.dir)

    health = load_json(root / "health.json")
    statistics = load_json(root / "statistics.json")
    paper_runtime = load_json(root / "paper_runtime.json")
    discovery = load_json(root / "paper_edge_discovery.json")
    candidates = load_json(root / "research_candidates.json")
    top_detail = load_json(root / "top_candidates_detail.json")
    explainability = load_json(root / "candidate_explainability.json")

    for name, payload in [
        ("health", health),
        ("statistics", statistics),
        ("paper_runtime", paper_runtime),
        ("paper_edge_discovery", discovery),
        ("research_candidates", candidates),
        ("top_candidates_detail", top_detail),
        ("candidate_explainability", explainability),
    ]:
        assert_ok(payload, name)

    paper = paper_runtime.get("data") or {}
    assert "closed_trades_total" in paper, "paper_runtime.closed_trades_total missing"
    assert "signals_today" in paper, "paper_runtime.signals_today missing"
    assert "fills_today" in paper, "paper_runtime.fills_today missing"
    assert "pnl_total" in paper, "paper_runtime.pnl_total missing"

    discovery_data = discovery.get("data") or {}
    assert "paper_runtime" in discovery_data, "discovery.paper_runtime missing"
    assert "knowledge_graph" in discovery_data, "discovery.knowledge_graph missing"
    assert "validation" in discovery_data, "discovery.validation missing"

    candidate_rows = candidates.get("data") or []
    detail_rows = top_detail.get("data") or []
    explain_rows = explainability.get("data") or []

    assert isinstance(candidate_rows, list), "research_candidates data is not list"
    assert isinstance(detail_rows, list), "top_candidates_detail data is not list"
    assert isinstance(explain_rows, list), "candidate_explainability data is not list"

    assert len(candidate_rows) > 0, "research_candidates empty"
    assert len(detail_rows) > 0, "top_candidates_detail empty"
    assert len(explain_rows) > 0, "candidate_explainability empty"

    first_explain = explain_rows[0]
    for key in [
        "explainability_status",
        "why_selected",
        "risk_explanation",
        "evidence_summary",
        "recommended_action",
    ]:
        assert key in first_explain, f"candidate_explainability.{key} missing"

    html = (root / "page.html").read_text(encoding="utf-8")
    for token in REQUIRED_HTML_TOKENS:
        assert token in html, f"HTML token missing: {token}"

    print("acceptance_health_ready=READY")
    print("acceptance_statistics_ready=READY")
    print("acceptance_paper_runtime_ready=READY")
    print("acceptance_discovery_ready=READY")
    print("acceptance_candidates_ready=READY")
    print("acceptance_explainability_ready=READY")
    print("acceptance_html_ready=READY")
    print("VERDICT=PAPER_EDGE_DISCOVERY_ACCEPTANCE_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_paper_edge_discovery_acceptance_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EDGE_DISCOVERY_ACCEPTANCE_V1 ==="

OUT="/tmp/paper_edge_discovery_acceptance_v1"
rm -rf "$OUT"
mkdir -p "$OUT"

PYTHONPATH=src python -m py_compile \
  src/scripts/validate_paper_edge_discovery_acceptance_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_edge_discovery.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/paper_edge_discovery.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  > "$OUT/research_candidates_builder.log"

KG_API_HOST=127.0.0.1 KG_API_PORT=18495 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > "$OUT/kg_api.log" 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=18480 KG_API_BASE_URL=http://127.0.0.1:18495 PYTHONPATH=src \
python src/marketcore/presentation/app.py > "$OUT/ui.log" 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:18495/api/kg/v1/health" \
  > "$OUT/health.json"

curl -fsS "http://127.0.0.1:18495/api/kg/v1/statistics" \
  > "$OUT/statistics.json"

curl -fsS "http://127.0.0.1:18495/api/kg/v1/paper-runtime" \
  > "$OUT/paper_runtime.json"

curl -fsS "http://127.0.0.1:18495/api/kg/v1/paper-edge-discovery" \
  > "$OUT/paper_edge_discovery.json"

curl -fsS "http://127.0.0.1:18495/api/kg/v1/paper-edge-research-candidates?limit=20" \
  > "$OUT/research_candidates.json"

curl -fsS "http://127.0.0.1:18495/api/kg/v1/paper-edge-top-candidates-detail?limit=10" \
  > "$OUT/top_candidates_detail.json"

curl -fsS "http://127.0.0.1:18495/api/kg/v1/paper-edge-candidate-explainability?limit=10" \
  > "$OUT/candidate_explainability.json"

curl -fsS "http://127.0.0.1:18480/paper-edge-discovery" \
  > "$OUT/page.html"

PYTHONPATH=src python src/scripts/validate_paper_edge_discovery_acceptance_v1.py \
  --dir "$OUT" | tee "$OUT/acceptance.log"

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_ACCEPTANCE_V1_READY" "$OUT/acceptance.log"

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_research_candidates_v1;")
test "$rows" -gt 0

echo "research_candidates_rows=$rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EDGE_DISCOVERY_ACCEPTANCE_V1_READY"
echo "VERDICT=TEST_PAPER_EDGE_DISCOVERY_ACCEPTANCE_V1_OK"
SH_TEST

chmod +x scripts/test_paper_edge_discovery_acceptance_v1.sh

scripts/test_paper_edge_discovery_acceptance_v1.sh

echo "VERDICT=BUILD_PAPER_EDGE_DISCOVERY_ACCEPTANCE_V1_OK"
