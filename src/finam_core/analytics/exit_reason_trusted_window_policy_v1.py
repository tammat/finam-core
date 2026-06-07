from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class TrustedWindowDecision:
    trusted: bool
    reason: str


class ExitReasonTrustedWindowPolicyV1:

    BR_TRUSTED_FROM = datetime(2026, 6, 5, tzinfo=timezone.utc)
    NG_TRUSTED_FROM = datetime(2026, 6, 3, tzinfo=timezone.utc)

    def evaluate(
        self,
        root_symbol: str,
        closed_at: datetime,
    ) -> TrustedWindowDecision:

        root = str(root_symbol).upper()

        if root == "BR":
            trusted = closed_at >= self.BR_TRUSTED_FROM

            return TrustedWindowDecision(
                trusted=trusted,
                reason=(
                    "br_exit_reason_trusted_window"
                    if trusted
                    else "br_exit_reason_untrusted_window"
                ),
            )

        if root == "NG":
            trusted = closed_at >= self.NG_TRUSTED_FROM

            return TrustedWindowDecision(
                trusted=trusted,
                reason=(
                    "ng_exit_reason_trusted_window"
                    if trusted
                    else "ng_exit_reason_untrusted_window"
                ),
            )

        return TrustedWindowDecision(
            trusted=False,
            reason="unknown_root",
        )
