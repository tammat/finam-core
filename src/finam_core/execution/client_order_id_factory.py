from __future__ import annotations

import time


class ClientOrderIdFactory:
    """Русский комментарий: генерирует устойчивый client_order_id для recovery."""

    def build(self, *, intent_id: int) -> str:
        return f"fc_i{int(intent_id)}_{int(time.time() * 1000)}"
