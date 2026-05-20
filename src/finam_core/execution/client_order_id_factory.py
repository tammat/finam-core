from __future__ import annotations

import time


class ClientOrderIdFactory:
    """Русский комментарий: генерирует устойчивый client_order_id для recovery."""

    def build(self, *, intent_id: int) -> str:
        return f"fc_i{int(intent_id)}_{int(time.time() * 1000)}"


def build_client_order_id(*, strategy: str, symbol: str, side: str) -> str:
    """Русский комментарий: совместимая функция для генерации client_order_id в execution scripts."""
    safe_strategy = str(strategy or "exec").lower().replace(" ", "_")
    safe_symbol = str(symbol or "UNKNOWN").replace("@", "_").replace("/", "_")
    safe_side = str(side or "NA").upper()
    base = ClientOrderIdFactory().build(intent_id=0)
    return f"{base}_{safe_strategy}_{safe_symbol}_{safe_side}"
