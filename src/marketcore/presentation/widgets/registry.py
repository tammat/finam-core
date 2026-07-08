from __future__ import annotations

from marketcore.presentation.widgets.contracts import WidgetDefinition


class WidgetRegistry:
    def __init__(self) -> None:
        self._items: dict[str, WidgetDefinition] = {}

    def register(self, definition: WidgetDefinition) -> None:
        if definition.widget_id in self._items:
            raise ValueError(f"WIDGET_ALREADY_REGISTERED={definition.widget_id}")
        self._items[definition.widget_id] = definition

    def get(self, widget_id: str) -> WidgetDefinition:
        return self._items[widget_id]

    def all(self) -> list[WidgetDefinition]:
        return sorted(self._items.values(), key=lambda item: item.priority)


def default_widget_registry() -> WidgetRegistry:
    registry = WidgetRegistry()
    registry.register(WidgetDefinition("best_edge", "widget.best_edge.title", "🎯", 10, "research"))
    registry.register(WidgetDefinition("shadow", "widget.shadow.title", "👁️", 20, "research"))
    registry.register(WidgetDefinition("daily", "widget.daily.title", "📊", 30, "analytics"))
    registry.register(WidgetDefinition("portfolio", "widget.portfolio.title", "💼", 40, "portfolio"))
    registry.register(WidgetDefinition("system", "widget.system.title", "⚙", 50, "system"))
    return registry
