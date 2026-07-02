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
