# -*- coding: utf-8 -*-
from __future__ import annotations

from finam_core.statistics.builders.base_builder import FactBuilder
from finam_core.statistics.builders.noop_builder import NoopFactBuilder
from finam_core.statistics.builders.workflow_event_fact_builder import WorkflowEventFactBuilder
from finam_core.statistics.builders.workflow_event_fact_builder import WorkflowEventFactBuilder


class BuilderRegistry:
    def __init__(self, cur=None) -> None:
        self._builders: dict[str, FactBuilder] = {
            "NOOP_FACT_BUILDER_V1": NoopFactBuilder(),
        }
        if cur is not None:
            self._builders["WORKFLOW_EVENT_FACT_BUILDER_V1"] = WorkflowEventFactBuilder(cur)

    def get(self, builder_name: str) -> FactBuilder | None:
        return self._builders.get(builder_name)
