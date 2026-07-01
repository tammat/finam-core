from __future__ import annotations

from marketcore.presentation.viewmodels.research_center_vm import (
    ResearchCenterVM,
    build_default_research_center_vm,
)


class ResearchCenterService:
    def load(self) -> ResearchCenterVM:
        return build_default_research_center_vm()
