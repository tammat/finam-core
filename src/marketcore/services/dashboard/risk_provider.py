from __future__ import annotations

from marketcore.presentation.viewmodels.executive_overview_vm import HomeMetricVM, HomeRiskVM


class RiskProvider:
    def load_platform_metric(self) -> HomeMetricVM:
        return HomeMetricVM("Риски", "HIGH", "HIGH", "План P1", "/risk")

    def load_risk(self) -> HomeRiskVM:
        return HomeRiskVM(
            title="Риски",
            value="HIGH",
            reason="Corr. risk",
            priority="P1",
            action_label="План P1",
            action_href="/risk",
        )
