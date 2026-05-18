from __future__ import annotations


def build_runtime_digest(rows: list[dict]) -> str:
    """Русский комментарий: краткий digest причин отсутствия ALERT."""

    if not rows:
        return "📊 Runtime Digest\n\nНет данных."

    lines = ["📊 Runtime Digest\n"]

    for row in rows[:15]:
        symbol = row.get("symbol", "UNKNOWN")
        reason = row.get("reason", "unknown")

        lines.append(f"{symbol} → {reason}")

    return "\n".join(lines)
