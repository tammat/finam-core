from .result import ClassifierResult


class ConflictResolver:
    # Вычисляет простой conflict_score.
    # V1: UNKNOWN увеличивает конфликтность, противоречивые пары будут добавлены позже.

    def resolve(self, results: tuple[ClassifierResult, ...]) -> float:
        if not results:
            return 1.0
        unknown_count = sum(1 for item in results if item.state == "UNKNOWN")
        return round(unknown_count / len(results), 6)
