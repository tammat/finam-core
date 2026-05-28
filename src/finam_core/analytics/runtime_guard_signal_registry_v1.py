from __future__ import annotations

import os
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from finam_core.analytics.runtime_guard_decision_adapter_v1 import RuntimeGuardDecision
from finam_core.analytics.statistics_repository import build_psycopg_url


class RuntimeGuardSignalRegistryV1:
    """
    Русский комментарий:
    Registry сохраняет runtime guard telemetry в PostgreSQL.
    Не влияет на execution/risk/OMS.
    """

    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.getenv("DATABASE_URL") or build_psycopg_url()

    def migrate(self) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                CREATE TABLE IF NOT EXISTS runtime_guard_signal_registry_v1 (
                    id BIGSERIAL PRIMARY KEY,
                    signal_id TEXT,
                    ts TIMESTAMPTZ NOT NULL DEFAULT now(),

                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT,
                    regime TEXT,
                    volatility_regime TEXT,
                    session_type TEXT,

                    guard_decision TEXT NOT NULL,
                    guard_reason TEXT NOT NULL DEFAULT '',
                    guard_matched BOOLEAN NOT NULL DEFAULT false,
                    runtime_soft_blocked BOOLEAN NOT NULL DEFAULT false,

                    closed_total BIGINT,
                    winrate DOUBLE PRECISION,
                    profit_factor DOUBLE PRECISION,
                    expectancy DOUBLE PRECISION,

                    confidence DOUBLE PRECISION,
                    rr DOUBLE PRECISION,
                    qty DOUBLE PRECISION,

                    fill_id TEXT,
                    trade_id BIGINT,
                    pnl DOUBLE PRECISION,
                    outcome_class TEXT,

                    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

                    UNIQUE(signal_id)
                );
                """)

                cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_runtime_guard_signal_registry_v1_symbol_ts
                ON runtime_guard_signal_registry_v1(symbol, ts DESC);
                """)

                cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_runtime_guard_signal_registry_v1_decision
                ON runtime_guard_signal_registry_v1(guard_decision, runtime_soft_blocked);
                """)

            conn.commit()

    @staticmethod
    def _features(signal: Any) -> dict[str, Any]:
        if isinstance(signal, dict):
            features = signal.get("features")
        else:
            features = getattr(signal, "features", None)

        return features if isinstance(features, dict) else {}

    @staticmethod
    def _get(signal: Any, key: str, default: Any = None) -> Any:
        if isinstance(signal, dict):
            return signal.get(key, default)

        return getattr(signal, key, default)

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except Exception:
            return None

    def save(self, *, signal: Any, decision: RuntimeGuardDecision) -> None:
        features = self._features(signal)

        signal_id = (
            self._get(signal, "signal_id")
            or features.get("signal_id")
            or None
        )

        payload = {
            "signal": signal if isinstance(signal, dict) else {},
            "features": features,
            "runtime_guard": {
                "decision": decision.decision,
                "reason": decision.reason,
                "matched": decision.matched,
                "closed_total": decision.closed_total,
                "winrate": decision.winrate,
                "profit_factor": decision.profit_factor,
                "expectancy": decision.expectancy,
            },
        }

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                INSERT INTO runtime_guard_signal_registry_v1 (
                    signal_id,
                    symbol,
                    strategy,
                    timeframe,
                    regime,
                    volatility_regime,
                    session_type,
                    guard_decision,
                    guard_reason,
                    guard_matched,
                    runtime_soft_blocked,
                    closed_total,
                    winrate,
                    profit_factor,
                    expectancy,
                    confidence,
                    rr,
                    qty,
                    payload
                )
                VALUES (
                    %(signal_id)s,
                    %(symbol)s,
                    %(strategy)s,
                    %(timeframe)s,
                    %(regime)s,
                    %(volatility_regime)s,
                    %(session_type)s,
                    %(guard_decision)s,
                    %(guard_reason)s,
                    %(guard_matched)s,
                    %(runtime_soft_blocked)s,
                    %(closed_total)s,
                    %(winrate)s,
                    %(profit_factor)s,
                    %(expectancy)s,
                    %(confidence)s,
                    %(rr)s,
                    %(qty)s,
                    %(payload)s
                )
                ON CONFLICT (signal_id)
                DO UPDATE SET
                    ts = now(),
                    symbol = excluded.symbol,
                    strategy = excluded.strategy,
                    timeframe = excluded.timeframe,
                    regime = excluded.regime,
                    volatility_regime = excluded.volatility_regime,
                    session_type = excluded.session_type,
                    guard_decision = excluded.guard_decision,
                    guard_reason = excluded.guard_reason,
                    guard_matched = excluded.guard_matched,
                    runtime_soft_blocked = excluded.runtime_soft_blocked,
                    closed_total = excluded.closed_total,
                    winrate = excluded.winrate,
                    profit_factor = excluded.profit_factor,
                    expectancy = excluded.expectancy,
                    confidence = excluded.confidence,
                    rr = excluded.rr,
                    qty = excluded.qty,
                    payload = excluded.payload;
                """, {
                    "signal_id": signal_id,
                    "symbol": decision.symbol,
                    "strategy": decision.strategy,
                    "timeframe": decision.timeframe,
                    "regime": decision.regime,
                    "volatility_regime": decision.volatility_regime,
                    "session_type": decision.session_type,
                    "guard_decision": decision.decision,
                    "guard_reason": decision.reason,
                    "guard_matched": decision.matched,
                    "runtime_soft_blocked": bool(features.get("runtime_soft_blocked")),
                    "closed_total": decision.closed_total,
                    "winrate": decision.winrate,
                    "profit_factor": decision.profit_factor,
                    "expectancy": decision.expectancy,
                    "confidence": self._float_or_none(self._get(signal, "confidence") or features.get("confidence")),
                    "rr": self._float_or_none(self._get(signal, "rr") or features.get("rr")),
                    "qty": self._float_or_none(self._get(signal, "qty") or features.get("qty")),
                    "payload": Jsonb(payload),
                })

            conn.commit()

        print(
            "RUNTIME_GUARD_SIGNAL_REGISTRY_SAVED "
            f"signal_id={signal_id} "
            f"symbol={decision.symbol} "
            f"strategy={decision.strategy} "
            f"decision={decision.decision} "
            f"soft_blocked={bool(features.get('runtime_soft_blocked'))}",
            flush=True,
        )
