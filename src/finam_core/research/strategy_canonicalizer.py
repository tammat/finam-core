from __future__ import annotations


def canonicalize_strategy_name(value: str | None) -> str:
    """
    Русский комментарий:
    Единый канонизатор имени стратегии.
    Нужен, чтобы BR_CONSERVATIVE_BREAKOUT и br_conservative_breakout
    не жили как разные стратегии.
    """
    raw = str(value or "").strip()

    if not raw:
        return ""

    return (
        raw.upper()
        .replace("-", "_")
        .replace(" ", "_")
        .replace("__", "_")
    )


def canonicalize_timeframe(value: str | None) -> str:
    """Русский комментарий: единый канонизатор timeframe."""
    return str(value or "").strip().upper()
