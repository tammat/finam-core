from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DesignComponent:
    name: str
    category: str
    status: str = "READY"


class DesignRegistry:
    def __init__(self) -> None:
        self._components: dict[str, DesignComponent] = {}

    def register(self, component: DesignComponent) -> None:
        self._components[component.name] = component

    def get(self, name: str) -> DesignComponent | None:
        return self._components.get(name)

    def list(self) -> list[DesignComponent]:
        return list(self._components.values())


design_registry = DesignRegistry()
