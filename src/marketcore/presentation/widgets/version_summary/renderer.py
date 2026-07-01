from __future__ import annotations

from marketcore.presentation.design_system.components.cards import KeyValueCard, VersionCard
from marketcore.presentation.design_system.layout.grid import DashboardGrid, SectionHeader
from marketcore.presentation.viewmodels.executive_overview_vm import ExecutiveOverviewVM


class VersionSummaryWidget:
    def render(self, vm: ExecutiveOverviewVM, lang: str = "ru") -> str:
        title = "Версии" if lang == "ru" else "Versions"

        cards = [
            VersionCard(vm.version.product_name, vm.version.product_version),
            KeyValueCard(
                "Сборка" if lang == "ru" else "Build",
                {
                    "Dashboard": vm.version.dashboard_version,
                    "Repo": vm.version.repo,
                    "Commit": vm.version.git_commit,
                    "Tag": vm.version.git_tag,
                },
            ),
        ]

        return SectionHeader(title) + DashboardGrid(cards)
