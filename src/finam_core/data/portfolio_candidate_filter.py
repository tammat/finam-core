# -*- coding: utf-8 -*-
from __future__ import annotations


class PortfolioAwareCandidateFilter:
    """
    Русский комментарий:
    Фильтр не торгует.
    Он определяет, является ли кандидат новой идеей или уже связан с позицией в портфеле.
    """

    def classify(self, candidate: dict, positions: dict[str, dict]) -> dict:
        symbol = str(candidate.get("symbol") or "")
        direction = str(candidate.get("direction") or "").upper()

        position = positions.get(symbol)

        result = dict(candidate)

        if not position:
            result["portfolio_status"] = "NEW_CANDIDATE"
            result["portfolio_action"] = "WATCH_FOR_ENTRY"
            return result

        qty = float(position.get("qty") or 0.0)

        if qty > 0:
            result["portfolio_status"] = "ALREADY_HELD_LONG"

            if direction == "GAINER":
                result["portfolio_action"] = "HOLD_OR_ADD_CHECK"
            elif direction == "LOSER":
                result["portfolio_action"] = "EXIT_WATCH"
            else:
                result["portfolio_action"] = "HOLD_ONLY"

            return result

        if qty < 0:
            result["portfolio_status"] = "ALREADY_HELD_SHORT"

            if direction == "LOSER":
                result["portfolio_action"] = "HOLD_OR_ADD_CHECK"
            elif direction == "GAINER":
                result["portfolio_action"] = "EXIT_WATCH"
            else:
                result["portfolio_action"] = "HOLD_ONLY"

            return result

        result["portfolio_status"] = "FLAT"
        result["portfolio_action"] = "WATCH_FOR_ENTRY"
        return result

    def apply(self, candidates: list[dict], positions: dict[str, dict]) -> list[dict]:
        return [self.classify(c, positions) for c in candidates]
