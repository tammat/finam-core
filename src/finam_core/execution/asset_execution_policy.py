# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AssetExecutionDecision:
    allowed: bool
    mode: str
    asset_class: str
    reason: str


class AssetExecutionPolicy:
    """
    Русский комментарий:
    Центральная политика допуска к реальному исполнению.
    До 01.07.2026 фьючерсы не исполняются real-режимом.
    """

    FUTURES_PREFIXES = ("BR", "NG", "SI", "RI", "MX", "MM")
    BOND_PREFIXES = ("SU", "RU")

    def decide(self, symbol: str) -> AssetExecutionDecision:
        symbol = str(symbol or "").upper()

        if not symbol:
            return AssetExecutionDecision(False, "BLOCK", "UNKNOWN", "empty_symbol")

        asset_class = self.detect_asset_class(symbol)

        if os.getenv("REAL_TRADING_ENABLED", "0") != "1":
            return AssetExecutionDecision(False, "BLOCK", asset_class, "real_trading_disabled")

        if os.path.exists(os.getenv("KILL_SWITCH_FILE", "/opt/finam-core/KILL_SWITCH")):
            return AssetExecutionDecision(False, "BLOCK", asset_class, "kill_switch_file_exists")

        if asset_class == "STOCK":
            if os.getenv("REAL_STOCK_TRADING_ENABLED", "0") != "1":
                return AssetExecutionDecision(False, "BLOCK", asset_class, "real_stock_trading_disabled")

            allowlist = {
                x.strip().upper()
                for x in os.getenv("REAL_STOCK_ALLOWLIST", "").split(",")
                if x.strip()
            }

            base = symbol.split("@", 1)[0]

            if allowlist and base not in allowlist and symbol not in allowlist:
                return AssetExecutionDecision(False, "BLOCK", asset_class, f"stock_not_in_allowlist:{symbol}")

            return AssetExecutionDecision(True, "REAL", asset_class, "stock_real_allowed")

        if asset_class == "FUTURES":
            return AssetExecutionDecision(False, "TELEGRAM_ONLY", asset_class, "futures_real_blocked_until_2026_07_01")

        if asset_class == "BOND":
            return AssetExecutionDecision(False, "BLOCK", asset_class, "bond_auto_trading_disabled")

        return AssetExecutionDecision(False, "SIGNAL_ONLY", asset_class, "asset_class_signal_only")

    def detect_asset_class(self, symbol: str) -> str:
        base = str(symbol or "").upper().split("@", 1)[0]

        if base.startswith(self.BOND_PREFIXES):
            return "BOND"

        if any(base.startswith(prefix) for prefix in self.FUTURES_PREFIXES):
            return "FUTURES"

        if "@MISX" in str(symbol).upper() or base.isalpha():
            return "STOCK"

        return "UNKNOWN"
