# -*- coding: utf-8 -*-
from __future__ import annotations

from abc import ABC, abstractmethod

from finam_core.statistics.pipeline.builder_context import BuilderContext
from finam_core.statistics.pipeline.builder_result import BuilderResult


class FactBuilder(ABC):
    @abstractmethod
    def build(self, context: BuilderContext) -> BuilderResult:
        raise NotImplementedError
