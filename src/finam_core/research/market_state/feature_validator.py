from typing import Any


class FeatureValidator:
    # Проверяет минимальный набор признаков. БД и Runtime не используются.

    REQUIRED_FIELDS = ("symbol", "timeframe", "close")

    def validate(self, features: dict[str, Any]) -> tuple[bool, list[str]]:
        missing = [name for name in self.REQUIRED_FIELDS if name not in features]
        return len(missing) == 0, missing
