from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class TaxProfileDTO:
    tax_profile_code: str
    account_scope: str
    country_code: str
    tax_rate: Decimal
    tax_mode: str
    source_version: str
