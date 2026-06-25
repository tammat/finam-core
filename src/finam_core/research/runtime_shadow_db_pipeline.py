from datetime import datetime, timezone
from typing import Any

from finam_core.research.events import MarketFeaturesReadyEvent
from finam_core.research.runtime_shadow_subscriber import RuntimeShadowSubscriber
from finam_core.research.event_adapter import ResearchEventAdapter
from finam_core.research.market_state.repository import MarketStateRepository


class RuntimeShadowDbPipeline:
    # Shadow DB pipeline получает копию runtime-события,
    # строит MarketStateBuiltEvent и сохраняет его только в research.*.
    # Runtime и Execution не изменяются.

    def __init__(
        self,
        database_url: str,
        adapter: ResearchEventAdapter | None = None,
        repository: MarketStateRepository | None = None,
    ) -> None:
        self.subscriber = RuntimeShadowSubscriber()
        self.adapter = adapter or ResearchEventAdapter()
        self.repository = repository or MarketStateRepository(database_url)

    def process_market_event(
        self,
        event: dict[str, Any],
        *,
        snapshot_ts: datetime | None = None,
        asset_class: str | None = None,
    ) -> dict[str, Any]:
        features_event: MarketFeaturesReadyEvent = self.subscriber.market_data_to_features_event(event)
        state_event = self.adapter.handle_market_features(features_event)

        snapshot_id = self.repository.save_market_state_event(
            state_event,
            snapshot_ts=snapshot_ts or datetime.now(timezone.utc),
            asset_class=asset_class or str(event.get("asset_class", "")) or None,
            source="runtime_shadow_market_state_v1",
        )

        return {
            "snapshot_id": snapshot_id,
            "symbol": state_event.symbol,
            "timeframe": state_event.timeframe,
            "canonical_signature": state_event.canonical_signature,
            "compact_signature": state_event.compact_signature,
            "quality": state_event.quality,
            "confidence": state_event.confidence,
            "orders_sent": state_event.payload.get("orders_sent", 0),
            "buy_sell_hold_decision": state_event.payload.get("buy_sell_hold_decision", "NONE"),
            "runtime_changed": 0,
            "execution_changed": 0,
            "real_trading_enabled": 0,
        }
