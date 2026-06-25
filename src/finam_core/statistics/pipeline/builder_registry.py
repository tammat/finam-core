# -*- coding: utf-8 -*-
from __future__ import annotations

from finam_core.statistics.builders.base_builder import FactBuilder
from finam_core.statistics.builders.noop_builder import NoopFactBuilder


class BuilderRegistry:
    def __init__(self) -> None:
        self._builders: dict[str, FactBuilder] = {
            "NOOP_FACT_BUILDER_V1": NoopFactBuilder(),
        }

    def get(self, builder_name: str) -> FactBuilder | None:
        return self._builders.get(builder_name)
