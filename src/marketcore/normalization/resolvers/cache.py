from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResolutionCache:
    values: dict[str, dict[str, Any]] = field(default_factory=dict)

    def contains(self, namespace: str, key: str) -> bool:
        return key in self.values.get(namespace, {})

    def get(self, namespace: str, key: str) -> Any | None:
        return self.values.get(namespace, {}).get(key)

    def set(self, namespace: str, key: str, value: Any | None) -> None:
        self.values.setdefault(namespace, {})[key] = value
