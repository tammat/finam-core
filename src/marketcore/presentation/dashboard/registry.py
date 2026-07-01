from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DashboardPage:
    key: str
    title_key: str
    path: str
    icon: str
    enabled: bool = True


class DashboardRegistry:
    def __init__(self) -> None:
        self._pages: dict[str, DashboardPage] = {}

    def register(self, page: DashboardPage) -> None:
        self._pages[page.key] = page

    def unregister(self, key: str) -> None:
        self._pages.pop(key, None)

    def get(self, key: str) -> DashboardPage | None:
        return self._pages.get(key)

    def list_pages(self) -> list[DashboardPage]:
        return list(self._pages.values())


registry = DashboardRegistry()

for page in [
    DashboardPage("home", "home", "/", "home"),
    DashboardPage("market", "market", "/market", "market"),
    DashboardPage("research", "research", "/research", "research"),
    DashboardPage("metadata", "metadata", "/metadata", "metadata"),
    DashboardPage("risk", "risk", "/risk", "risk"),
    DashboardPage("runtime", "runtime", "/runtime", "runtime"),
    DashboardPage("remediation", "remediation", "/remediation", "remediation"),
    DashboardPage("versions", "versions", "/versions", "versions"),
    DashboardPage("system", "system", "/system", "system"),
]:
    registry.register(page)
