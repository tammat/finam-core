from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Page:
    route: str
    title: str
    icon: str
    menu_order: int

    def render(self) -> str:
        raise NotImplementedError("Page.render() must be implemented")
