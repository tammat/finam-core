# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersistenceResult:
    symbol: str
    appearances: int
    avg_score: float
    last_score: float
    score_delta: float
    avg_relative_strength: float
    last_relative_strength: float
    state: str


class RadarPersistenceEngine:
    """
    Русский комментарий:
    Анализирует устойчивость попадания инструмента в market_radar_results.
    Не торгует и не отправляет заявки.
    """

    def classify(self, rows: list[dict]) -> PersistenceResult | None:
        if not rows:
            return None

        sorted_rows = sorted(rows, key=lambda x: x.get("ts"))

        symbol = str(sorted_rows[-1].get("symbol") or "")
        appearances = len(sorted_rows)

        scores = [float(r.get("score") or 0.0) for r in sorted_rows]
        rs_values = [float(r.get("relative_strength") or 0.0) for r in sorted_rows]

        avg_score = sum(scores) / len(scores)
        last_score = scores[-1]
        first_score = scores[0]
        score_delta = last_score - first_score

        avg_rs = sum(rs_values) / len(rs_values)
        last_rs = rs_values[-1]

        state = self._state(
            appearances=appearances,
            score_delta=score_delta,
            last_score=last_score,
            last_rs=last_rs,
        )

        return PersistenceResult(
            symbol=symbol,
            appearances=appearances,
            avg_score=round(avg_score, 4),
            last_score=round(last_score, 4),
            score_delta=round(score_delta, 4),
            avg_relative_strength=round(avg_rs, 4),
            last_relative_strength=round(last_rs, 4),
            state=state,
        )

    def _state(
        self,
        appearances: int,
        score_delta: float,
        last_score: float,
        last_rs: float,
    ) -> str:
        if appearances <= 1:
            return "ONE_SHOT"

        if appearances == 2:
            if score_delta > 0:
                return "WATCH_ACCELERATING"
            return "WATCH"

        if appearances >= 3:
            if score_delta > 1.0 and last_rs > 1.0:
                return "STRONG_INTRADAY"
            if score_delta > 0:
                return "STABLE_ACCELERATING"
            if score_delta < -1.0:
                return "FADING"
            return "STABLE_CANDIDATE"

        return "UNKNOWN"
