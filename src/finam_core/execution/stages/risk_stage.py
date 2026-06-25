# -*- coding: utf-8 -*-
from __future__ import annotations

from finam_core.execution.stages.base_stage import WorkflowStage
from finam_core.execution.workflow.context import WorkflowContext
from finam_core.execution.workflow.result import WorkflowResult


class RiskStage(WorkflowStage):
    # V1: безопасная заглушка RiskStage.
    # Реальная risk-логика будет подключена отдельным этапом.

    def execute(self, context: WorkflowContext) -> WorkflowResult:
        return WorkflowResult(
            status="OK",
            next_stage=context.next_stage,
            reason="RISK_STAGE_STUB_OK",
            payload={
                "stage": "RISK",
                "risk_logic": "STUB_ONLY",
                "runtime_changed": False,
                "execution_changed": False,
                "orders_changed": False,
                "fills_changed": False,
                "micro_live_allowed": False,
            },
        )
