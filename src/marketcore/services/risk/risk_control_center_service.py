from __future__ import annotations

from marketcore.presentation.viewmodels.risk_control_center_vm import (
    RiskControlCenterVM,
    build_default_risk_control_center_vm,
)


class RiskControlCenterService:
    def load(self) -> RiskControlCenterVM:
        return build_default_risk_control_center_vm()
