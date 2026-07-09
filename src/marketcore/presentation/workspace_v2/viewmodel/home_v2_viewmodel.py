from __future__ import annotations

from dataclasses import dataclass

from marketcore.presentation.framework.base_layout import BaseLayout


@dataclass(frozen=True, slots=True)
class HomeV2ViewModel:
    layout: BaseLayout
