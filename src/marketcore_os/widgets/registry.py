from __future__ import annotations

from typing import Iterable

from marketcore_os.widgets.base import Widget


class WidgetRegistry:
    def __init__(self) -> None:
        self._widgets: list[Widget] = []

    def register(self, widget: Widget) -> None:
        if any(existing.widget_id == widget.widget_id for existing in self._widgets):
            raise ValueError(f"duplicate widget_id: {widget.widget_id}")
        self._widgets.append(widget)

    def all(self) -> list[Widget]:
        return sorted(self._widgets, key=lambda w: (w.priority, w.widget_id))

    def for_workspace(self, workspace: str) -> list[Widget]:
        return [widget for widget in self.all() if widget.workspace == workspace]


registry = WidgetRegistry()


def register(widget: Widget) -> None:
    registry.register(widget)


def widgets_for_workspace(workspace: str) -> Iterable[Widget]:
    return registry.for_workspace(workspace)


def all_widgets() -> Iterable[Widget]:
    return registry.all()


def bootstrap_widgets() -> None:
    if list(registry.all()):
        return

    from marketcore_os.widgets.today import today_widget
    from marketcore_os.widgets.capital import capital_widget
    from marketcore_os.widgets.profit import profit_widget
    from marketcore_os.widgets.program import program_widget

    register(today_widget)
    register(capital_widget)
    register(profit_widget)
    register(program_widget)


bootstrap_widgets()
