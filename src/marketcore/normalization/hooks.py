from __future__ import annotations

from marketcore.normalization.context import NormalizationContext


class NormalizationHooks:
    def before_pipeline(self, ctx: NormalizationContext) -> None:
        return None

    def after_pipeline(self, ctx: NormalizationContext) -> None:
        return None

    def before_step(self, step_name: str, ctx: NormalizationContext) -> None:
        return None

    def after_step(self, step_name: str, ctx: NormalizationContext) -> None:
        return None
