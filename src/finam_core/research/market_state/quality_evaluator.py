from .types import MarketStateQuality


class QualityEvaluator:
    # Преобразует conflict_score в категорию качества.

    def evaluate(self, conflict_score: float, valid_features: bool) -> MarketStateQuality:
        if not valid_features:
            return MarketStateQuality.INVALID_FEATURE_SET
        if conflict_score == 0:
            return MarketStateQuality.GOOD
        if conflict_score < 0.5:
            return MarketStateQuality.WEAK
        if conflict_score < 1.0:
            return MarketStateQuality.CONFLICTED
        return MarketStateQuality.UNKNOWN
