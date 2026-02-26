from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .base import TradingSession
from .crypto import CryptoSession
from .cme import CmeSession
from .moex import MoexSession


@dataclass(frozen=True)
class SessionService:
    moex: TradingSession = MoexSession()
    cme: TradingSession = CmeSession()
    crypto: TradingSession = CryptoSession()

    def get(self, exchange: str) -> TradingSession:
        key = (exchange or "").strip().lower()
        if key in {"moex", "micex", "misx"}:
            return self.moex
        if key in {"cme", "globex"}:
            return self.cme
        if key in {"crypto", "binance", "bybit", "okx"}:
            return self.crypto
        raise ValueError(f"Unknown exchange: {exchange!r}")

    def is_open(self, exchange: str, now: datetime) -> bool:
        return self.get(exchange).is_open(now)

    def next_open(self, exchange: str, now: datetime) -> datetime:
        return self.get(exchange).next_open(now)

    def next_close(self, exchange: str, now: datetime) -> datetime:
        return self.get(exchange).next_close(now)