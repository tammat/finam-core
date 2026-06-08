from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NgSmartEntryQualityDecisionV1:
    allowed: bool
    action: str
    reason: str


class NgSmartEntryQualityGateV1:
    """Русский комментарий: защитный gate для NG smart_entry_retest в плохом режиме."""

    def evaluate(
        self,
        *,
        root_symbol: str,
        entry_reason: str,
        regime: str,
    ) -> NgSmartEntryQualityDecisionV1:
        root = str(root_symbol or "").upper()
        reason = str(entry_reason or "").lower()
        regime_value = str(regime or "").lower()

        if root != "NG":
            return NgSmartEntryQualityDecisionV1(True, "PASS", "not_ng")

        if reason != "smart_entry_retest":
            return NgSmartEntryQualityDecisionV1(True, "PASS", "not_smart_entry_retest")

        if regime_value == "trend_down_high_vol":
            return NgSmartEntryQualityDecisionV1(
                False,
                "BLOCK",
                "ng_smart_entry_retest_trend_down_high_vol_block",
            )

        return NgSmartEntryQualityDecisionV1(True, "ALLOW", "quality_gate_pass")
