from __future__ import annotations

from marketcore.presentation.pages.edge_pipeline_v2 import EdgePipelineV2Page
from marketcore.presentation.ui_labels import display_label


class EdgePipelineV2PaperEdgeDiscoveryAliasPage(EdgePipelineV2Page):
    route = "/paper-edge-discovery"
    title = display_label(route, "Edge")


class EdgePipelineV2ValidationQueueAliasPage(EdgePipelineV2Page):
    route = "/edge-validation-queue"
    title = display_label(route, "Проверка")


class EdgePipelineV2ValidationPipelineAliasPage(EdgePipelineV2Page):
    route = "/edge-validation-pipeline"
    title = display_label(route, "Этапы")


class EdgePipelineV2RobustnessAliasPage(EdgePipelineV2Page):
    route = "/edge-robustness-check"
    title = display_label(route, "Устойчивость")


class EdgePipelineV2OosValidationAliasPage(EdgePipelineV2Page):
    route = "/edge-oos-validation"
    title = display_label(route, "Вне выборки")


class EdgePipelineV2OosBacktestAliasPage(EdgePipelineV2Page):
    route = "/edge-oos-backtest"
    title = display_label(route, "Тест вне выборки")


class EdgePipelineV2MicroLiveAliasPage(EdgePipelineV2Page):
    route = "/micro-live-readiness"
    title = display_label(route, "Проба")
