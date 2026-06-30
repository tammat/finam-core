#!/usr/bin/env python3
from __future__ import annotations

SOURCES = [
    ("Market", "Finam Runtime", "finam_runtime", "bar", "market_bar", "READY", "stream", "hot+cold", "runtime,research,strategy", False),
    ("Market", "Finam History", "finam_history", "bar", "market_bar", "READY", "batch", "cold", "research,feature", True),
    ("Market", "MOEX History", "moex_history", "bar", "market_bar", "PLANNED", "batch", "cold", "research,feature", True),
    ("Research", "Generated", "research_generator", "synthetic_event", "research_event", "READY", "batch", "cold", "research", True),
    ("Research", "Replay", "replay_engine", "trade_replay", "replay_trade", "READY", "batch", "cold", "research,edge", True),
    ("Trading", "Paper Trading", "paper_execution", "paper_fill", "paper_trade", "READY", "event", "hot+cold", "portfolio,risk,research", True),
    ("Trading", "Runtime Trading", "runtime_execution", "runtime_fill", "runtime_trade", "BLOCKED_FOR_LIVE", "event", "hot+cold", "portfolio,risk,audit", False),
    ("Broker", "Broker", "finam_broker", "broker_event", "broker_trade", "PARTIAL", "event", "hot+cold", "execution,portfolio,audit", False),
    ("Strategy", "Strategy", "strategy_engine", "signal", "strategy_signal", "READY", "event", "hot+cold", "risk,research,execution", True),
    ("Research", "Research", "research_pipeline", "research_result", "research_candidate", "READY", "batch", "cold", "edge,governance", True),
    ("Feature", "Feature", "feature_builder", "feature", "feature_vector", "READY", "batch", "cold", "strategy,ai,research", True),
    ("AI", "AI", "ai_layer", "ai_score", "ai_recommendation", "GATED_NO_ORDER_ACCESS", "batch", "cold", "research,governance", True),
]

def main() -> None:
    print("=== DATA_SOURCE_REGISTRY_BUILD_V1 ===")

    for row in SOURCES:
        domain, source_origin, producer, entity_type, canonical_entity, status, update_mode, retention, consumer, reproducible = row
        print(
            "REGISTRY"
            f"|domain={domain}"
            f"|source_origin={source_origin}"
            f"|producer={producer}"
            f"|entity_type={entity_type}"
            f"|canonical_entity={canonical_entity}"
            f"|normalization_status={status}"
            f"|update_mode={update_mode}"
            f"|retention_policy={retention}"
            f"|consumer={consumer}"
            f"|is_reproducible={int(reproducible)}"
        )

    print(f"sources={len(SOURCES)}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=DATA_SOURCE_REGISTRY_BUILD_V1_READY")

if __name__ == "__main__":
    main()
