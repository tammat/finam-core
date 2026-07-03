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
