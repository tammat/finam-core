# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class AttentionDecision:
    """Русский комментарий: портфельное решение внимания, не торговая заявка."""

    symbol: str
    action: str
    priority: float
    risk_multiplier: float
    reason: str
    current_qty: float = 0.0
    candidate_score: float = 0.0
    regime: str = "unknown"
    pnl_pct: float = 0.0


class AttentionAllocator:
    """Русский комментарий: распределяет внимание между позициями портфеля и scanner-кандидатами."""

    ACTION_HOLD = "HOLD"
    ACTION_TIGHTEN_STOP = "TIGHTEN_STOP"
    ACTION_REDUCE = "REDUCE"
    ACTION_ADD_CANDIDATE = "ADD_CANDIDATE"
    ACTION_ROTATION_CANDIDATE = "ROTATION_CANDIDATE"
    ACTION_WATCH = "WATCH"

    def __init__(self, *, high_score: float = 3.0, rotation_score_gap: float = 0.75) -> None:
        self.high_score = float(high_score)
        self.rotation_score_gap = float(rotation_score_gap)

    def allocate_attention(
        self,
        *,
        positions: dict[str, Any],
        candidates: Iterable[Any],
        max_active_symbols: int = 10,
    ) -> list[AttentionDecision]:
        candidate_map = {self._candidate_symbol(c): c for c in candidates if self._candidate_symbol(c)}
        portfolio_symbols = set(positions.keys())
        all_symbols = portfolio_symbols | set(candidate_map.keys())

        portfolio_scores = [self._candidate_score(candidate_map[s]) for s in portfolio_symbols if s in candidate_map]
        best_portfolio_score = max(portfolio_scores) if portfolio_scores else 0.0

        decisions: list[AttentionDecision] = []

        for symbol in sorted(all_symbols):
            pos = positions.get(symbol, {}) or {}
            candidate = candidate_map.get(symbol)

            qty = self._position_qty(pos)
            pnl_pct = self._position_pnl_pct(pos)
            score = self._candidate_score(candidate)
            regime = self._candidate_regime(candidate)

            adverse = self._is_adverse(qty, regime)
            aligned = self._is_aligned(qty, regime)

            action, reason, risk_multiplier = self._decide(
                in_portfolio=symbol in portfolio_symbols,
                qty=qty,
                score=score,
                regime=regime,
                pnl_pct=pnl_pct,
                adverse=adverse,
                aligned=aligned,
                best_portfolio_score=best_portfolio_score,
            )

            priority = self._priority(
                qty=qty,
                score=score,
                pnl_pct=pnl_pct,
                adverse=adverse,
                aligned=aligned,
                action=action,
            )

            decisions.append(
                AttentionDecision(
                    symbol=symbol,
                    action=action,
                    priority=priority,
                    risk_multiplier=risk_multiplier,
                    reason=reason,
                    current_qty=qty,
                    candidate_score=score,
                    regime=regime,
                    pnl_pct=pnl_pct,
                )
            )

        return sorted(decisions, key=lambda d: d.priority, reverse=True)[:max_active_symbols]

    def _decide(
        self,
        *,
        in_portfolio: bool,
        qty: float,
        score: float,
        regime: str,
        pnl_pct: float,
        adverse: bool,
        aligned: bool,
        best_portfolio_score: float,
    ) -> tuple[str, str, float]:
        if in_portfolio and qty != 0:
            if adverse and score >= self.high_score:
                return self.ACTION_REDUCE, f"adverse_high_vol_regime:{regime}", 0.25
            if adverse:
                return self.ACTION_TIGHTEN_STOP, f"adverse_regime:{regime}", 0.50
            if aligned and score >= self.high_score and pnl_pct >= 0:
                return self.ACTION_ADD_CANDIDATE, f"aligned_high_score:{regime}", 1.25
            if score <= 0:
                return self.ACTION_TIGHTEN_STOP, "not_in_scanner_or_score_zero", 0.50
            return self.ACTION_HOLD, "portfolio_symbol_scanner_passed", 1.00

        if not in_portfolio and score > 0:
            if score >= best_portfolio_score + self.rotation_score_gap and score >= self.high_score:
                return self.ACTION_ROTATION_CANDIDATE, "score_beats_portfolio_candidates", 0.75
            return self.ACTION_WATCH, "scanner_candidate_watch", 0.25

        return self.ACTION_WATCH, "no_position_no_candidate", 0.0

    @staticmethod
    def _priority(*, qty: float, score: float, pnl_pct: float, adverse: bool, aligned: bool, action: str) -> float:
        base = max(score, 0.0)
        if qty != 0:
            base += 0.75
        if adverse:
            base += 1.50
        if aligned:
            base += 0.50
        if action == "REDUCE":
            base += 2.00
        elif action == "TIGHTEN_STOP":
            base += 1.25
        elif action == "ROTATION_CANDIDATE":
            base += 1.00
        elif action == "ADD_CANDIDATE":
            base += 0.75
        if pnl_pct < -0.02:
            base += 0.75
        return round(min(base, 10.0), 6)

    @staticmethod
    def _candidate_symbol(candidate: Any) -> str:
        if candidate is None:
            return ""
        if isinstance(candidate, dict):
            return str(candidate.get("symbol") or "")
        return str(getattr(candidate, "symbol", "") or "")

    @staticmethod
    def _candidate_score(candidate: Any) -> float:
        if candidate is None:
            return 0.0
        value = candidate.get("score") if isinstance(candidate, dict) else getattr(candidate, "score", 0.0)
        try:
            return float(value or 0.0)
        except Exception:
            return 0.0

    @staticmethod
    def _candidate_regime(candidate: Any) -> str:
        if candidate is None:
            return "unknown"
        value = candidate.get("regime") if isinstance(candidate, dict) else getattr(candidate, "regime", "unknown")
        return str(value or "unknown")

    @staticmethod
    def _position_qty(pos: Any) -> float:
        value = pos.get("qty", pos.get("quantity", 0.0)) if isinstance(pos, dict) else getattr(pos, "qty", 0.0)
        try:
            return float(value or 0.0)
        except Exception:
            return 0.0

    @staticmethod
    def _position_pnl_pct(pos: Any) -> float:
        value = pos.get("pnl_pct", 0.0) if isinstance(pos, dict) else getattr(pos, "pnl_pct", 0.0)
        try:
            return float(value or 0.0)
        except Exception:
            return 0.0

    @staticmethod
    def _is_adverse(qty: float, regime: str) -> bool:
        r = str(regime or "").lower()
        if qty > 0 and "down" in r:
            return True
        if qty < 0 and "up" in r:
            return True
        return False

    @staticmethod
    def _is_aligned(qty: float, regime: str) -> bool:
        r = str(regime or "").lower()
        if qty > 0 and "up" in r:
            return True
        if qty < 0 and "down" in r:
            return True
        return False
