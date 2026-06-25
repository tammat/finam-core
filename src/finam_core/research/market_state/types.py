from enum import Enum


class MarketStateQuality(str, Enum):
    # Категории качества состояния рынка.
    GOOD = "GOOD"
    WEAK = "WEAK"
    CONFLICTED = "CONFLICTED"
    UNKNOWN = "UNKNOWN"
    INVALID_FEATURE_SET = "INVALID_FEATURE_SET"


class MarketStateEventType(str, Enum):
    # События event-driven pipeline Research Platform.
    FEATURE_VALIDATED = "FeatureValidatedEvent"
    FEATURE_NORMALIZED = "FeatureNormalizedEvent"
    CLASSIFIER_COMPLETED = "ClassifierCompletedEvent"
    CONFLICT_RESOLVED = "ConflictResolvedEvent"
    QUALITY_EVALUATED = "QualityEvaluatedEvent"
    MARKET_STATE_BUILT = "MarketStateBuiltEvent"
    SIGNATURE_BUILT = "SignatureBuiltEvent"
