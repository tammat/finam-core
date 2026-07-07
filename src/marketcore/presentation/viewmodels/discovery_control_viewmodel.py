from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DiscoveryControlViewModel:
    status: dict
    queue: list[dict]
    worker: list[dict]
    scheduler: dict
    audit: list[dict]
    bottleneck: dict
    events: list[dict]
    actions: list[dict]
