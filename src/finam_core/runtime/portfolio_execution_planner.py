from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionPlanItem:
    symbol: str

    decision: str

    priority: int

    allocated_capital: float
    allocated_qty: int

    quality_score: float
    quality_grade: str

    expected_value: float

    reason: str


class PortfolioExecutionPlanner:
    """Русский комментарий: формирует institutional execution queue."""

    def build_plan(
        self,
        *,
        candidates: list[dict],

        max_execute: int = 3,
        min_quality_score: float = 45.0,
    ) -> list[ExecutionPlanItem]:

        filtered: list[dict] = []

        for candidate in candidates:

            quality_score = float(candidate.get("quality_score") or 0.0)
            expected_value = float(candidate.get("expected_value") or 0.0)

            if quality_score < min_quality_score:
                continue

            if expected_value <= 0:
                continue

            filtered.append(candidate)

        filtered.sort(
            key=lambda x: (
                float(x.get("quality_score") or 0.0),
                float(x.get("expected_value") or 0.0),
            ),
            reverse=True,
        )

        plan: list[ExecutionPlanItem] = []

        used_groups: set[str] = set()

        priority = 1

        for idx, candidate in enumerate(filtered):

            symbol = str(candidate.get("symbol") or "")
            group = str(candidate.get("correlation_group") or "UNKNOWN")

            quality_score = float(candidate.get("quality_score") or 0.0)
            quality_grade = str(candidate.get("quality_grade") or "D")

            allocated_capital = float(candidate.get("allocated_capital") or 0.0)
            allocated_qty = int(candidate.get("allocated_qty") or 0)

            expected_value = float(candidate.get("expected_value") or 0.0)

            if group in used_groups:
                decision = "WATCH"
                reason = f"sector already allocated: {group}"

            elif priority <= max_execute:
                decision = "EXECUTE"
                reason = (
                    f"top_quality={quality_score:.2f};"
                    f"grade={quality_grade};"
                    f"expected_value={expected_value:.2f}"
                )
                used_groups.add(group)
                priority += 1

            else:
                decision = "WATCH"
                reason = "execution_limit_reached"

            plan.append(
                ExecutionPlanItem(
                    symbol=symbol,

                    decision=decision,

                    priority=idx + 1,

                    allocated_capital=round(allocated_capital, 2),
                    allocated_qty=allocated_qty,

                    quality_score=quality_score,
                    quality_grade=quality_grade,

                    expected_value=round(expected_value, 2),

                    reason=reason,
                )
            )

        return plan
