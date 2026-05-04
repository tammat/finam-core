# -*- coding: utf-8 -*-
from __future__ import annotations

import os


def env_symbol_key(symbol: str) -> str:
    return (
        symbol.upper()
        .replace("@", "_")
        .replace("-", "_")
        .replace(".", "_")
        .replace("/", "_")
    )


class RegimePolicy:
    """Русский комментарий: разрешённые режимы по инструментам через env."""

    def allowed_regimes_for(self, symbol: str) -> set[str]:
        key = f"ALLOWED_REGIMES_{env_symbol_key(symbol)}"
        raw = os.getenv(key, "").strip()
        if not raw:
            return set()
        return {x.strip() for x in raw.split(",") if x.strip()}

    def is_allowed(self, symbol: str, regime: str) -> tuple[bool, str]:
        allowed = self.allowed_regimes_for(symbol)

        if "__DISABLED__" in allowed:
            return False, "REGIME_POLICY_DISABLED_SYMBOL"

        if not allowed:
            return True, "REGIME_POLICY_NOT_CONFIGURED"

        if regime in allowed:
            return True, f"REGIME_ALLOWED:{regime}"

        return False, f"REGIME_BLOCKED:{regime}"
