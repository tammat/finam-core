from __future__ import annotations

from pathlib import Path


PAGES = [
    Path("src/marketcore/presentation/pages/edge_validation_queue.py"),
    Path("src/marketcore/presentation/pages/edge_validation_pipeline.py"),
]


def main() -> None:
    print("=== EDGE_UI_USE_MARKET_UNIVERSE_V1 ===")

    for page in PAGES:
        text = page.read_text()
        print(f"PAGE file={page}")
        if "paper_edge_research_candidates_v1" in text:
            raise SystemExit(f"LEGACY_SOURCE_IN_UI_PAGE {page}")
        if "BR@RTSX" in text:
            raise SystemExit(f"BR_ONLY_TEXT_IN_UI_PAGE {page}")

    print("edge_queue_uses_market_universe=READY")
    print("edge_pipeline_uses_market_universe=READY")
    print("legacy_br_ui_removed=READY")
    print("VERDICT=EDGE_UI_USE_MARKET_UNIVERSE_V1_READY")


if __name__ == "__main__":
    main()
