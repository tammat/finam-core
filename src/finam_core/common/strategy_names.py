# -*- coding: utf-8 -*-
from __future__ import annotations


CANONICAL_STRATEGY_NAMES = {
    "br_conservative_breakout": "BR_CONSERVATIVE_BREAKOUT",
    "BR_CONSERVATIVE_BREAKOUT": "BR_CONSERVATIVE_BREAKOUT",
}


def normalize_strategy_name(value: str | None) -> str:
    """Русский комментарий: единая нормализация имени стратегии для research/runtime слоёв."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    return CANONICAL_STRATEGY_NAMES.get(raw, CANONICAL_STRATEGY_NAMES.get(raw.lower(), raw))
