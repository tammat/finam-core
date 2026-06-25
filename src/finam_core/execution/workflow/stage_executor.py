# -*- coding: utf-8 -*-
from __future__ import annotations

from finam_core.execution.stages.risk_stage import RiskStage
from finam_core.execution.stages.signal_stage import SignalStage
from finam_core.execution.workflow.context import WorkflowContext
from finam_core.execution.workflow.result import WorkflowResult


class StageExecutor:
    # Диспетчер stage-плагинов. Workflow Engine не содержит бизнес-логику.

    def __init__(self) -> None:
        self._stages = {
            "RISK": RiskStage(),
            "SIGNAL": SignalStage(),
        }

    def execute(self, context: WorkflowContext) -> WorkflowResult:
        stage = self._stages.get(context.current_stage)
        if stage is None:
            return WorkflowResult(
                status="FAIL",
                next_stage=context.current_stage,
                reason=f"STAGE_PLUGIN_NOT_FOUND:{context.current_stage}",
                payload={"stage": context.current_stage},
            )
        return stage.execute(context)
