from __future__ import annotations

import psycopg
from finam_core.analytics.statistics_repository import build_psycopg_url


class FuturesRegimeGovernanceRepository:
    """
    Русский комментарий:
    Governance gate для фьючерсов на основе futures_mtf_regime.
    Не меняет стратегию напрямую, а формирует отдельный слой решений.
    """

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or build_psycopg_url()

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS futures_regime_governance (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL UNIQUE,
            root_symbol TEXT NOT NULL,

            macro_regime TEXT NOT NULL DEFAULT 'unknown',
            macro_trend TEXT NOT NULL DEFAULT 'unknown',
            execution_regime TEXT NOT NULL DEFAULT 'unknown',
            execution_trend TEXT NOT NULL DEFAULT 'unknown',
            volatility_state TEXT NOT NULL DEFAULT 'unknown',
            bias_alignment TEXT NOT NULL DEFAULT 'unknown',

            futures_tradable BOOLEAN NOT NULL DEFAULT FALSE,
            allow_runtime BOOLEAN NOT NULL DEFAULT FALSE,
            allow_paper BOOLEAN NOT NULL DEFAULT FALSE,
            allow_research BOOLEAN NOT NULL DEFAULT TRUE,

            governance_action TEXT NOT NULL DEFAULT 'RESEARCH_ONLY',
            reason TEXT NOT NULL DEFAULT '',

            calculated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_futures_regime_governance_root
        ON futures_regime_governance(root_symbol, allow_runtime, allow_paper);
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def rebuild(self) -> int:
        sql = """
        INSERT INTO futures_regime_governance (
            symbol,
            root_symbol,
            macro_regime,
            macro_trend,
            execution_regime,
            execution_trend,
            volatility_state,
            bias_alignment,
            futures_tradable,
            allow_runtime,
            allow_paper,
            allow_research,
            governance_action,
            reason,
            calculated_at
        )
        SELECT
            symbol,
            root_symbol,
            macro_regime,
            macro_trend,
            execution_regime,
            execution_trend,
            volatility_state,
            bias_alignment,
            tradable AS futures_tradable,

            CASE
                WHEN tradable = TRUE
                 AND bias_alignment IN ('aligned', 'range_aligned')
                 AND volatility_state IN ('normal', 'high')
                THEN TRUE
                ELSE FALSE
            END AS allow_runtime,

            CASE
                WHEN tradable = TRUE
                 AND bias_alignment IN ('aligned', 'range_aligned')
                THEN TRUE
                ELSE FALSE
            END AS allow_paper,

            TRUE AS allow_research,

            CASE
                WHEN tradable = FALSE THEN 'BLOCK_RUNTIME'
                WHEN bias_alignment = 'conflict' THEN 'RESEARCH_ONLY'
                WHEN volatility_state = 'low' THEN 'PAPER_ONLY_LOW_VOL'
                WHEN volatility_state IN ('normal', 'high')
                  AND bias_alignment IN ('aligned', 'range_aligned')
                THEN 'ALLOW_PAPER_RUNTIME_CANDIDATE'
                ELSE 'RESEARCH_ONLY'
            END AS governance_action,

            CASE
                WHEN tradable = FALSE THEN reason
                WHEN bias_alignment = 'conflict' THEN 'futures_mtf_conflict'
                WHEN volatility_state = 'low' THEN 'aligned_but_low_volatility'
                WHEN volatility_state IN ('normal', 'high')
                  AND bias_alignment IN ('aligned', 'range_aligned')
                THEN 'futures_regime_allows_runtime_candidate'
                ELSE 'futures_regime_requires_research'
            END AS reason,

            now()
        FROM futures_mtf_regime
        ON CONFLICT (symbol)
        DO UPDATE SET
            root_symbol = EXCLUDED.root_symbol,
            macro_regime = EXCLUDED.macro_regime,
            macro_trend = EXCLUDED.macro_trend,
            execution_regime = EXCLUDED.execution_regime,
            execution_trend = EXCLUDED.execution_trend,
            volatility_state = EXCLUDED.volatility_state,
            bias_alignment = EXCLUDED.bias_alignment,
            futures_tradable = EXCLUDED.futures_tradable,
            allow_runtime = EXCLUDED.allow_runtime,
            allow_paper = EXCLUDED.allow_paper,
            allow_research = EXCLUDED.allow_research,
            governance_action = EXCLUDED.governance_action,
            reason = EXCLUDED.reason,
            calculated_at = now()
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                saved = cur.rowcount
            conn.commit()

        return int(saved or 0)
