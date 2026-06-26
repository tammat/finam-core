from __future__ import annotations

from marketcore.catalog.discovery.executor import DiscoveryPlugin


class DiscoveryRegistry:
    version = "DISCOVERY_REGISTRY_V1"

    def __init__(self) -> None:
        self._plugins: list[DiscoveryPlugin] = []

    def register(self, plugin: DiscoveryPlugin) -> None:
        self._plugins.append(plugin)

    def plugins(self) -> list[DiscoveryPlugin]:
        return list(self._plugins)
