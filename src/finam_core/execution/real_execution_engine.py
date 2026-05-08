from __future__ import annotations

import logging

from finam_core.execution.asset_execution_policy import AssetExecutionPolicy

logger = logging.getLogger(__name__)


class RealExecutionEngine:
    def __init__(self, broker, *args, **kwargs):
        self.broker = broker
        self.asset_policy = AssetExecutionPolicy()

    def execute(self, signal):
        decision = self.asset_policy.decide(signal.symbol)

        if not decision.allowed:
            logger.warning(
                "REAL_EXECUTION_BLOCKED "
                "symbol=%s asset_class=%s mode=%s reason=%s",
                signal.symbol,
                decision.asset_class,
                decision.mode,
                getattr(decision, "reason", "blocked"),
            )

            return {
                "success": False,
                "status": "blocked_by_policy",
                "symbol": signal.symbol,
                "reason": getattr(decision, "reason", "blocked"),
            }

        logger.info(
            "REAL_EXECUTION_ALLOWED "
            "symbol=%s asset_class=%s mode=%s",
            signal.symbol,
            decision.asset_class,
            decision.mode,
        )

        return self._submit_order(signal)

    def _submit_order(self, signal):
        return self.broker.submit_order(signal)
