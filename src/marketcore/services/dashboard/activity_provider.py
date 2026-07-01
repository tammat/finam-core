from __future__ import annotations

from marketcore.presentation.viewmodels.executive_overview_vm import HomeActivityVM


class ActivityProvider:
    def load(self) -> list[HomeActivityVM]:
        return [
            HomeActivityVM("Now", "Home data model ready"),
            HomeActivityVM("Now", "Base page ready"),
            HomeActivityVM("Now", "Component preview ready"),
            HomeActivityVM("Now", "Design system ready"),
        ]
