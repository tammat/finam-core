# src/finam_core/execution/execution_fill.py
# Русский коммент: единый контракт исполнения (paper/real) для всего движка.

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True, slots=True)
class ExecutionFill:
    """
    Русский коммент:
    Единый формат fill для всех режимов.
    - qty всегда ПОЛОЖИТЕЛЬНЫЙ
    - направление хранится в side ("BUY"/"SELL")
    """
    fill_id: str
    symbol: str
    side: str
    qty: float
    price: float
    commission: float = 0.0
    timestamp: datetime = datetime.now(timezone.utc)
    origin: str = "unknown"          # paper|real|sim|replay|etc
    account_id: Optional[str] = None

    def __post_init__(self) -> None:
        # Русский коммент: нормализуем side/числа и проверяем инварианты.
        side = str(self.side).upper()
        if side not in ("BUY", "SELL"):
            raise ValueError(f"ExecutionFill: invalid side={self.side!r}")
        object.__setattr__(self, "side", side)

        q = float(self.qty)
        p = float(self.price)
        c = float(self.commission)

        if q < 0:
            raise ValueError("ExecutionFill: qty must be >= 0 (direction is in side)")
        if p < 0:
            raise ValueError("ExecutionFill: price must be >= 0")
        if c < 0:
            raise ValueError("ExecutionFill: commission must be >= 0")

        object.__setattr__(self, "qty", q)
        object.__setattr__(self, "price", p)
        object.__setattr__(self, "commission", c)

        ts = self.timestamp
        if ts is None:
            object.__setattr__(self, "timestamp", datetime.now(timezone.utc))
        elif getattr(ts, "tzinfo", None) is None:
            # Русский коммент: наивное время считаем UTC
            object.__setattr__(self, "timestamp", ts.replace(tzinfo=timezone.utc))

    @classmethod
    def from_paper(cls, paper_fill, *, side: str, origin: str = "paper", account_id: Optional[str] = None) -> "ExecutionFill":
        """
        Русский коммент: PaperFill -> ExecutionFill.
        PaperFill в проекте часто не несёт side, поэтому side берём из intent.
        """
        return cls(
            fill_id=str(getattr(paper_fill, "fill_id", "")) or "paper_fill_missing_id",
            symbol=str(getattr(paper_fill, "symbol", None) or getattr(paper_fill, "instrument", None) or ""),
            side=str(side).upper(),
            qty=abs(float(getattr(paper_fill, "qty", 0.0) or 0.0)),
            price=float(getattr(paper_fill, "price", 0.0) or 0.0),
            commission=float(getattr(paper_fill, "commission", 0.0) or 0.0),
            timestamp=datetime.now(timezone.utc),
            origin=origin,
            account_id=account_id,
        )