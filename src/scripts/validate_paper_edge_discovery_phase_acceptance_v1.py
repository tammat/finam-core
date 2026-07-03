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
