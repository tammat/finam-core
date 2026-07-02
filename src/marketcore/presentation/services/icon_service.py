from __future__ import annotations


class IconService:
    ICONS = {
        "home": "⌂",
        "runtime": "▶",
        "knowledge_graph": "◎",
        "research": "⌕",
        "portfolio": "◈",
        "orders": "⇄",
        "risk": "⚠",
        "validation": "✓",
        "logs": "≡",
        "system": "⚙",
        "ai": "✦",
        "paper": "□",
        "edge": "◇",
        "capital": "₽",
        "signal": "→",
        "trade": "◆",
        "fill": "■",
    }

    def icon(self, key: str) -> str:
        return self.ICONS.get(key, "•")
