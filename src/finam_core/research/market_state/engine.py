from typing import Any

from .classifier_pipeline import ClassifierPipeline
from .conflict_resolver import ConflictResolver
from .explanation_builder import ExplanationBuilder
from .feature_normalizer import FeatureNormalizer
from .feature_validator import FeatureValidator
from .quality_evaluator import QualityEvaluator
from .result import MarketStateEvent, MarketStateResult
from .signature_builder import SignatureBuilder
from .types import MarketStateEventType


class MarketStateEngine:
    # Event-driven core implementation V1.
    # Engine не является стратегией, не генерирует сигналы и не отправляет заявки.

    def __init__(self) -> None:
        self.validator = FeatureValidator()
        self.normalizer = FeatureNormalizer()
        self.pipeline = ClassifierPipeline()
        self.conflict_resolver = ConflictResolver()
        self.quality_evaluator = QualityEvaluator()
        self.signature_builder = SignatureBuilder()
        self.explanation_builder = ExplanationBuilder()

    def build(self, features: dict[str, Any]) -> MarketStateResult:
        events: list[MarketStateEvent] = []

        valid, missing = self.validator.validate(features)
        events.append(
            MarketStateEvent(
                event_type=MarketStateEventType.FEATURE_VALIDATED.value,
                payload={"valid": valid, "missing": missing},
            )
        )

        normalized = self.normalizer.normalize(features)
        events.append(
            MarketStateEvent(
                event_type=MarketStateEventType.FEATURE_NORMALIZED.value,
                payload={"symbol": normalized.get("symbol"), "timeframe": normalized.get("timeframe")},
            )
        )

        classifier_results = self.pipeline.run(normalized) if valid else tuple()
        events.append(
            MarketStateEvent(
                event_type=MarketStateEventType.CLASSIFIER_COMPLETED.value,
                payload={"results": len(classifier_results)},
            )
        )

        conflict_score = self.conflict_resolver.resolve(classifier_results)
        events.append(
            MarketStateEvent(
                event_type=MarketStateEventType.CONFLICT_RESOLVED.value,
                payload={"conflict_score": conflict_score},
            )
        )

        quality = self.quality_evaluator.evaluate(conflict_score, valid)
        events.append(
            MarketStateEvent(
                event_type=MarketStateEventType.QUALITY_EVALUATED.value,
                payload={"quality": quality.value},
            )
        )

        canonical_signature = self.signature_builder.build_canonical(classifier_results)
        compact_signature = self.signature_builder.build_compact(canonical_signature)
        events.append(
            MarketStateEvent(
                event_type=MarketStateEventType.SIGNATURE_BUILT.value,
                payload={
                    "canonical_signature": canonical_signature,
                    "compact_signature": compact_signature,
                },
            )
        )

        explanation = self.explanation_builder.build(classifier_results, conflict_score)
        events.append(
            MarketStateEvent(
                event_type=MarketStateEventType.MARKET_STATE_BUILT.value,
                payload={"explanation_lines": len(explanation)},
            )
        )

        confidence = 0.0
        if classifier_results:
            confidence = round(
                sum(item.confidence for item in classifier_results) / len(classifier_results),
                6,
            )

        return MarketStateResult(
            symbol=str(normalized.get("symbol", "UNKNOWN")),
            timeframe=str(normalized.get("timeframe", "UNKNOWN")),
            canonical_signature=canonical_signature,
            compact_signature=compact_signature,
            quality=quality.value,
            confidence=confidence,
            conflict_score=conflict_score,
            explanation_tree_ru=explanation,
            classifier_results=classifier_results,
            events=tuple(events),
            orders_sent=0,
            buy_sell_hold_decision="NONE",
        )
