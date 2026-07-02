from __future__ import annotations

import json
import os
from urllib.error import URLError
from urllib.request import urlopen


KG_API_BASE_URL = os.getenv("KG_API_BASE_URL", "http://127.0.0.1:8095")


def get_json(path: str, timeout: float = 2.0) -> dict:
    url = KG_API_BASE_URL.rstrip("/") + path
    try:
        with urlopen(url, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {
            "status": "ERROR",
            "data": {},
            "metadata": {
                "error": type(exc).__name__,
                "message": str(exc),
                "url": url,
            },
        }
