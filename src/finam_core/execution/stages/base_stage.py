# -*- coding: utf-8 -*-
from __future__ import annotations

from abc import ABC, abstractmethod

from finam_core.execution.workflow.context import WorkflowContext
from finam_core.execution.workflow.result import WorkflowResult


class WorkflowStage(ABC):
    # Базовый интерфейс всех stage-плагинов.

    @abstractmethod
    def execute(self, context: WorkflowContext) -> WorkflowResult:
        raise NotImplementedError
