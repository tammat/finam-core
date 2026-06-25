from typing import Any

from finam_core.research.events import MarketFeaturesReadyEvent, MarketStateBuiltEvent
from finam_core.research.market_state import MarketStateEngine


class ResearchEventAdapter:
    # Граница между общей event-driven архитектурой и Research Platform.
    # Adapter не импортирует Runtime, Execution, Broker adapters и не отправляет заявки.

    def __init__(self, engine: MarketStateEngine | None = None) -> None:
        self.engine = engine or MarketStateEngine()

    def convert_to_market_features(self, event: MarketFeaturesReadyEvent | dict[str, Any]) -> dict[str, Any]:
        # Приводит входное событие к словарю признаков для MarketStateEngine.
        if isinstance(event, MarketFeaturesReadyEvent):
            features = dict(event.features)
            features.setdefault("symbol", event.symbol)
            features.setdefault("timeframe", event.timeframe)
            return features

        features = dict(event.get("features", event))
        if "symbol" in event:
            features.setdefault("symbol", event["symbol"])
        if "timeframe" in event:
            features.setdefault("timeframe", event["timeframe"])
        return features

    def handle_market_features(self, event: MarketFeaturesReadyEvent | dict[str, Any]) -> MarketStateBuiltEvent:
        # Обрабатывает рыночные признаки и публикуемый результат возвращает как событие.
        features = self.convert_to_market_features(event)
        result = self.engine.build(features)

        return MarketStateBuiltEvent(
            symbol=result.symbol,
            timeframe=result.timeframe,
            canonical_signature=result.canonical_signature,
            compact_signature=result.compact_signature,
            quality=result.quality,
            confidence=result.confidence,
            payload={
                "conflict_score": result.conflict_score,
                "explanation_tree_ru": result.explanation_tree_ru,
                "classifier_results": [
                    {
                        "group": item.group,
                        "state": item.state,
                        "confidence": item.confidence,
                        "classifier_version": item.classifier_version,
                    }
                    for item in result.classifier_results
                ],
                "engine_events": [
                    {
                        "event_type": item.event_type,
                        "payload": item.payload,
                    }
                    for item in result.events
                ],
                "orders_sent": result.orders_sent,
                "buy_sell_hold_decision": result.buy_sell_hold_decision,
            },
        )
