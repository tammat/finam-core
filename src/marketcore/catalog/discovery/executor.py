from __future__ import annotations

from typing import Protocol

from marketcore.catalog.discovery.context import DiscoveryContext
from marketcore.catalog.discovery.result import DiscoveredObject


class DiscoveryPlugin(Protocol):
    name: str
    version: str

    def discover(self, context: DiscoveryContext) -> list[DiscoveredObject]:
        ...


class DiscoveryExecutor:
    version = "DISCOVERY_EXECUTOR_V1"

    def __init__(self, plugins: list[DiscoveryPlugin]) -> None:
        self.plugins = plugins

    def run(self, context: DiscoveryContext) -> list[DiscoveredObject]:
        objects: list[DiscoveredObject] = []

        for plugin in self.plugins:
            objects.extend(plugin.discover(context))

        unique: dict[str, DiscoveredObject] = {}
        for obj in objects:
            unique[obj.object_id] = obj

        return list(unique.values())
