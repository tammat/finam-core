from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class FinamOrderIdentity:
    broker_order_id: str | None
    broker_exec_id: str | None
    client_order_id: str | None
    status: str | None


class FinamOrderIdentityExtraction:
    """Русский комментарий: извлекает order_id / exec_id / client_order_id из ответа Finam."""

    def extract(self, result) -> FinamOrderIdentity:
        text = str(result)

        if isinstance(result, dict):
            raw = result.get("raw") or {}
            ack = raw.get("ack") if isinstance(raw, dict) else {}
            raw_response = ""

            if isinstance(ack, dict):
                raw_response = str((ack.get("raw") or {}).get("response") or "")

            return FinamOrderIdentity(
                broker_order_id=(
                    result.get("order_id")
                    or result.get("broker_order_id")
                    or self._match(raw_response, r'order_id:\s*"([^"]+)"')
                ),
                broker_exec_id=self._match(raw_response, r'exec_id:\s*"([^"]+)"'),
                client_order_id=self._match(raw_response, r'client_order_id:\s*"([^"]+)"'),
                status=(
                    result.get("status")
                    or self._match(raw_response, r"status:\s*(ORDER_STATUS_[A-Z_]+)")
                ),
            )

        return FinamOrderIdentity(
            broker_order_id=self._match(text, r'order_id:\s*"([^"]+)"'),
            broker_exec_id=self._match(text, r'exec_id:\s*"([^"]+)"'),
            client_order_id=self._match(text, r'client_order_id:\s*"([^"]+)"'),
            status=self._match(text, r"status:\s*(ORDER_STATUS_[A-Z_]+)"),
        )

    def _match(self, text: str, pattern: str) -> str | None:
        m = re.search(pattern, text or "")
        return m.group(1) if m else None
