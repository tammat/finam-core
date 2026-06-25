from typing import Any


class FeatureNormalizer:
    # Детерминированно нормализует признаки для классификаторов.

    def normalize(self, features: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(features)
        normalized["symbol"] = str(normalized.get("symbol", "UNKNOWN"))
        normalized["timeframe"] = str(normalized.get("timeframe", "UNKNOWN"))
        if "close" in normalized:
            normalized["close"] = float(normalized["close"])
        return normalized
