from __future__ import annotations

import time


class ClientOrderIdFactory:
    """Русский комментарий: генерирует устойчивый client_order_id для recovery."""

    def build(self, *, intent_id: int) -> str:
        return f"fc_i{int(intent_id)}_{int(time.time() * 1000)}"


def build_client_order_id(*, strategy: str, symbol: str, side: str) -> str:
    """Русский комментарий: генерирует client_order_id длиной не более 20 символов для Finam."""
    import time

    safe_side = str(side or "X").upper()[:1]
    safe_strategy = str(strategy or "x").lower()[:2]
    # Finam ограничивает client_order_id 20 символами.
    # Формат: fc + 12 цифр времени + сторона + 2 символа стратегии = 17 символов.
    millis_tail = str(int(time.time() * 1000))[-12:]
    return f"fc{millis_tail}{safe_side}{safe_strategy}"[:20]

