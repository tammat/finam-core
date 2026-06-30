from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from marketcore.normalization.context import NormalizationContext


class PipelineStep(Protocol):
    name: str

    def run(self, ctx: NormalizationContext) -> NormalizationContext:
        ...


@dataclass(frozen=True)
class NormalizationPipeline:
    steps: tuple[PipelineStep, ...]
    stop_on_reject: bool = True

    def run(self, ctx: NormalizationContext) -> NormalizationContext:
        ctx.increment("pipeline_started", 1)

        for step in self.steps:
            ctx.increment(f"step_{step.name}_started", 1)

            result = step.run(ctx)

            ctx.increment(f"step_{step.name}_finished", 1)

            if self.stop_on_reject and not result.success:
                ctx.increment("pipeline_stopped_on_reject", 1)
                break

        ctx.increment("pipeline_finished", 1)
        return ctx
