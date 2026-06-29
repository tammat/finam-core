from __future__ import annotations

import json
from typing import Any


def dumps_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def empty_payload() -> dict[str, Any]:
    return {}
