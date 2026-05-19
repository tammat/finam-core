from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GrowthDigestRow:
    symbol: str
    decision: str
    score: float
    expected_value: float
    risk_pct: float
    qty: float
    rr: float
    mode: str
    reason: str


class CapitalGrowthTelegramDigest:
    """Русский комментарий: формирует Telegram digest по режиму разгона."""

    def build(
        self,
        *,
        profile: str,
        rows: list[GrowthDigestRow],
    ) -> str:
        lines: list[str] = []

        lines.append(f"🚀 РЕЖИМ РАЗГОНА [{profile.upper()}]")
        lines.append("")

        if not rows:
            lines.append("Нет активных growth setup.")
            return "\n".join(lines)

        for idx, row in enumerate(rows[:10], start=1):
            lines.extend([
                f"{idx}. {row.symbol}",
                f"decision={row.decision}",
                f"score={row.score:.2f}",
                f"EV={row.expected_value:.2f}",
                f"risk={row.risk_pct * 100:.2f}%",
                f"qty={row.qty:.2f}",
                f"RR={row.rr:.2f}",
                f"mode={row.mode}",
                f"reason={row.reason}",
                "",
            ])

        return "\n".join(lines).strip()
