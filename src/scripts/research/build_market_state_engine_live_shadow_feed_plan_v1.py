#!/usr/bin/env python3

# ==========================================================
# MARKET_STATE_ENGINE_LIVE_SHADOW_FEED_PLAN_V1
#
# План подключения Market State Engine к live shadow feed.
#
# ВАЖНО:
# - это НЕ включение реальной торговли;
# - Runtime не изменяется;
# - Execution не изменяется;
# - реальные заявки не отправляются;
# - Market State Engine получает только копию live market events.
# ==========================================================

print("=== MARKET_STATE_ENGINE_LIVE_SHADOW_FEED_PLAN_V1 ===")
print("mode=live_shadow_feed_plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

print("\nLIVE_SHADOW_FEED_FLOW")
flow = [
    ("LiveMarketData", "market_event_copy"),
    ("ResearchShadowSubscriber", "market_features_event"),
    ("ResearchEventAdapter", "market_state_built_event"),
    ("MarketStateRepository", "research_db_write"),
    ("ValidationScript", "shadow_feed_healthcheck"),
]
for src, dst in flow:
    print(f"FLOW from={src} to={dst}")

print("\nLIVE_SHADOW_FEED_RULES")
rules = [
    "live_feed_is_copy_only",
    "live_feed_never_blocks_runtime",
    "live_feed_never_sends_orders",
    "live_feed_never_changes_execution",
    "live_feed_writes_research_schema_only",
    "live_feed_failures_are_logged_not_raised_to_runtime",
    "shadow_feed_validation_required",
]
for rule in rules:
    print(f"RULE name={rule}")

print("\nREQUIRED_INPUT_FIELDS")
fields = [
    "symbol",
    "timeframe",
    "close",
    "trend_optional",
    "volatility_optional",
    "session_optional",
    "asset_class_optional",
    "event_ts_optional",
]
for field in fields:
    print(f"FIELD name={field}")

print("\nFILE_STRUCTURE")
files = [
    "src/finam_core/research/live_shadow_feed.py",
    "scripts/test_market_state_engine_live_shadow_feed_plan_v1.sh",
]
for file in files:
    print(f"FILE path={file}")

print("\nNEXT_STEPS")
print("next=MARKET_STATE_ENGINE_LIVE_SHADOW_FEED_IMPLEMENTATION_V1")
print("next=MARKET_STATE_ENGINE_LIVE_SHADOW_FEED_VALIDATION_V1")

print("\nVERDICT=MARKET_STATE_ENGINE_LIVE_SHADOW_FEED_PLAN_READY")
