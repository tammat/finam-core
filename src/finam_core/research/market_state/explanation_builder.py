from .result import ClassifierResult


class ExplanationBuilder:
    # Формирует русское дерево объяснения.

    def build(self, results: tuple[ClassifierResult, ...], conflict_score: float) -> list[str]:
        lines = [f"conflict_score={conflict_score}"]
        for item in results:
            lines.append(
                f"{item.group}={item.state}; confidence={item.confidence}; reason={item.explanation_ru}"
            )
        return lines
