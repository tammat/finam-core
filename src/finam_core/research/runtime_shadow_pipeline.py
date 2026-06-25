from datetime import datetime, timezone
from typing import Any

from finam_core.research.event_adapter import ResearchEventAdapter
from finam_core.research.runtime_shadow_subscriber import RuntimeShadowSubscriber


class RuntimeShadowPipeline:
    # Shadow pipeline строит состояние рынка по копии runtime-события.
    # Не отправляет заявки и не меняет runtime/execution.

    def __init__(self, adapter: ResearchEventAdapter | None = None) -> None:
        self.subscriber = RuntimeShadowSubscriber()
        self.adapter = adapter or ResearchEventAdapter()

    def process_market_event(self, event: dict[str, Any]) -> dict[str, Any]:
        features_event = self.subscriber.market_data_to_features_event(event)
        state_event = self.adapter.handle_market_features(features_event)

        return {
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "symbol": state_event.symbol,
            "timeframe": state_event.timeframe,
            "canonical_signature": state_event.canonical_signature,
            "compact_signature": state_event.compact_signature,
            "quality": state_event.quality,
            "confidence": state_event.confidence,
            "orders_sent": state_event.payload.get("orders_sent", 0),
            "buy_sell_hold_decision": state_event.payload.get("buy_sell_hold_decision", "NONE"),
            "event_type": "MarketStateBuiltEvent",
        }
