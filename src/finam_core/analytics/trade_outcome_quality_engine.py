from __future__ import annotations


class TradeOutcomeQualityEngine:
    """Русский комментарий: агрегированная статистика качества explainability/outcomes."""

    @staticmethod
    def summarize(rows: list[dict]) -> dict:
        total = len(rows)

        grades = {
            "A": 0,
            "B": 0,
            "C": 0,
            "D": 0,
        }

        regime_known = 0
        partition_isolated = 0

        for row in rows:
            grade = str(row.get("quality_grade", "D"))
            grades[grade] = grades.get(grade, 0) + 1

            if row.get("regime_known"):
                regime_known += 1

            if row.get("partition_isolated"):
                partition_isolated += 1

        return {
            "rows": total,
            "grades": grades,
            "regime_known_pct": round(regime_known / total, 4) if total else 0.0,
            "partition_isolated_pct": round(partition_isolated / total, 4) if total else 0.0,
        }
