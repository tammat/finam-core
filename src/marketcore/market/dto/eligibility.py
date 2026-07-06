from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EligibilityDTO:
    market_universe_code: str
    account_scope: str
    requires_qualified: bool
    requires_futures_access: bool
    requires_options_access: bool
    requires_margin_access: bool
    is_allowed: bool
    source_version: str
