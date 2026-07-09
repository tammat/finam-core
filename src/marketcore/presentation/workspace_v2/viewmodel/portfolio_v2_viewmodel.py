from __future__ import annotations

from dataclasses import dataclass

from marketcore.presentation.framework.base_section import BaseSection


@dataclass(frozen=True, slots=True)
class PortfolioV2ViewModel:
    title_key: str
    subtitle_key: str
    sections: tuple[BaseSection, ...]
