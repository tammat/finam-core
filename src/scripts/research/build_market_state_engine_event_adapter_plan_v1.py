#!/usr/bin/env python3

# ==========================================================
# MARKET_STATE_ENGINE_EVENT_ADAPTER_PLAN_V1
#
# План интеграции Research Platform с существующей
# Event-Driven архитектурой Finam_Core.
#
# ВАЖНО:
# - новый Event Bus НЕ создается;
# - используется существующая событийная модель;
# - Adapter является единственной точкой интеграции.
# ==========================================================

print("=== MARKET_STATE_ENGINE_EVENT_ADAPTER_PLAN_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

print("\nARCHITECTURE")

print("PRODUCER name=MarketData")
print("EVENT name=MarketFeaturesReadyEvent")
print("CONSUMER name=ResearchEventAdapter")

print("PRODUCER name=ResearchEventAdapter")
print("EVENT name=FeatureValidatedEvent")
print("CONSUMER name=MarketStateEngine")

print("PRODUCER name=MarketStateEngine")
print("EVENT name=MarketStateBuiltEvent")
print("CONSUMER name=EdgeDiscoveryEngine")

print("PRODUCER name=EdgeDiscoveryEngine")
print("EVENT name=EdgeDiscoveredEvent")
print("CONSUMER name=StrategyRecommendationEngine")

print("PRODUCER name=StrategyRecommendationEngine")
print("EVENT name=StrategyRecommendedEvent")
print("CONSUMER name=MicroLivePreparation")

print("\nEVENTS")

events = [
    "MarketFeaturesReadyEvent",
    "FeatureValidatedEvent",
    "FeatureNormalizedEvent",
    "ClassifierCompletedEvent",
    "ConflictResolvedEvent",
    "QualityEvaluatedEvent",
    "MarketStateBuiltEvent",
    "SignatureBuiltEvent",
    "EdgeDiscoveredEvent",
    "StrategyRecommendedEvent",
    "MicroLiveCandidateEvent",
]

for event in events:
    print(f"EVENT name={event}")

print("\nADAPTER_RESPONSIBILITIES")

responsibilities = [
    "subscribe_market_events",
    "convert_to_research_features",
    "publish_research_events",
    "never_modify_runtime",
    "never_send_orders",
    "never_import_execution",
]

for r in responsibilities:
    print(f"RESPONSIBILITY name={r}")

print("\nDESIGN_RULES")

rules = [
    "single_event_bus",
    "research_uses_adapter",
    "adapter_is_boundary",
    "market_state_engine_is_consumer",
    "edge_discovery_is_subscriber",
    "recommendation_is_subscriber",
    "dashboard_can_subscribe",
    "replay_can_subscribe",
    "telemetry_can_subscribe",
    "no_runtime_execution_changes",
]

for r in rules:
    print(f"rule={r}")

print("\nFILE_STRUCTURE")

files = [
    "src/finam_core/research/event_adapter.py",
    "src/finam_core/research/events.py",
    "scripts/test_market_state_engine_event_adapter_plan_v1.sh",
]

for f in files:
    print(f"FILE path={f}")

print("\nNEXT_STEPS")
print("next=MARKET_STATE_ENGINE_EVENT_ADAPTER_IMPLEMENTATION_V1")

print("\nVERDICT=MARKET_STATE_ENGINE_EVENT_ADAPTER_PLAN_READY")
