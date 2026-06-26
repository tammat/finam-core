from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DiscoveryContext:
    profile: str
    domain: str
    schema_filter: tuple[str, ...]
    name_patterns: tuple[str, ...]
