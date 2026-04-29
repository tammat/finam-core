# src/finam_core/risk/correlation_risk.py

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class CorrelationRiskDecision:
    allowed: bool
    reason: str
    symbol: str
    bucket: str
    current_bucket_exposure: float
    projected_bucket_exposure: float
    bucket_limit: float


class CorrelationRiskEngine:
    """
    Русский коммент: Correlation/Exposure Risk Layer.
    Минимальная версия: контролирует кластерный риск через asset bucket.
    Не отправляет заявки напрямую.
    """

    def __init__(self):
        self.bucket_limit = float(os.getenv("CORR_BUCKET_LIMIT", "0.35"))
        self.default_bucket = os.getenv("CORR_DEFAULT_BUCKET", "unknown")

    def bucket_for_symbol(self, symbol: str) -> str:
        s = str(symbol or "").upper()

        # Русский коммент: энергетика.
        if s.startswith("BR") or s.startswith("NG"):
            return "energy"

        # Русский коммент: валюта / доллар-рубль.
        if "USDRUB" in s or s.startswith("SI") or s.startswith("USD"):
            return "fx"

        # Русский коммент: акции/прочее.
        if "@MISX" in s:
            return "equity"

        return self.default_bucket

    def evaluate(
        self,
        symbol: str,
        portfolio_value: float,
        current_bucket_exposure: float,
        new_trade_value: float,
    ) -> CorrelationRiskDecision:
        bucket = self.bucket_for_symbol(symbol)

        pv = float(portfolio_value or 0.0)
        exposure = abs(float(current_bucket_exposure or 0.0))
        trade_value = abs(float(new_trade_value or 0.0))

        if pv <= 0:
            return CorrelationRiskDecision(
                allowed=False,
                reason="invalid_portfolio_value",
                symbol=symbol,
                bucket=bucket,
                current_bucket_exposure=0.0,
                projected_bucket_exposure=0.0,
                bucket_limit=self.bucket_limit,
            )

        current_ratio = exposure / pv
        projected_ratio = (exposure + trade_value) / pv

        if projected_ratio > self.bucket_limit:
            return CorrelationRiskDecision(
                allowed=False,
                reason="bucket_exposure_exceeded",
                symbol=symbol,
                bucket=bucket,
                current_bucket_exposure=current_ratio,
                projected_bucket_exposure=projected_ratio,
                bucket_limit=self.bucket_limit,
            )

        return CorrelationRiskDecision(
            allowed=True,
            reason="ok",
            symbol=symbol,
            bucket=bucket,
            current_bucket_exposure=current_ratio,
            projected_bucket_exposure=projected_ratio,
            bucket_limit=self.bucket_limit,
        )
