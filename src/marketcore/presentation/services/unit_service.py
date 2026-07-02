from __future__ import annotations


class UnitService:
    UNITS = {
        "contract": "контр.",
        "lot": "лот",
        "share": "шт.",
        "barrel": "барр.",
        "tick": "тик",
        "atr": "ATR",
        "rr": "RR",
        "pf": "PF",
        "expectancy": "матожидание",
        "pnl": "P&L",
        "drawdown": "просадка",
        "signal": "сигнал",
        "trade": "сделка",
        "fill": "исполнение",
        "edge": "edge",
    }

    def label(self, key: str) -> str:
        return self.UNITS.get(key, key)
