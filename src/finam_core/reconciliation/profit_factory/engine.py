from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


ENGINE_VERSION = "PROFIT_FACTORY_RECONCILIATION_ENGINE_V1"


@dataclass
class ReconciliationResult:
    run_id: str
    mode: str
    status: str = "COMPLETED"
    source_rows: int = 0
    created_rows: int = 0
    updated_rows: int = 0
    conflict_rows: int = 0
    stale_rows: int = 0
    skipped_rows: int = 0


class ProfitFactoryReconciliationEngine:
    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def run(self, *, dry_run: bool = False) -> ReconciliationResult:
        result = ReconciliationResult(
            run_id=str(uuid4()),
            mode="DRY_RUN" if dry_run else "APPLY",
        )
        started_at = datetime.now(timezone.utc)

        try:
            with self.connection.cursor() as cur:
                self._start_run(cur, result, started_at)
                rows = self._load_exact_paper_evidence(cur)
                result.source_rows = len(rows)

                for row in rows:
                    outcome = self._reconcile_paper_row(cur, row, dry_run=dry_run)
                    if outcome == "CREATED":
                        result.created_rows += 1
                    elif outcome == "UPDATED":
                        result.updated_rows += 1
                    elif outcome == "CONFLICT":
                        result.conflict_rows += 1
                    else:
                        result.skipped_rows += 1

                direct_rows = self._load_direct_runtime_production_evidence(cur)
                result.source_rows += len(direct_rows)
                for row in direct_rows:
                    outcome = self._reconcile_direct_evidence(cur, row, dry_run=dry_run)
                    if outcome == "CREATED":
                        result.created_rows += 1
                    elif outcome == "UPDATED":
                        result.updated_rows += 1
                    elif outcome == "CONFLICT":
                        result.conflict_rows += 1
                    else:
                        result.skipped_rows += 1

                if result.conflict_rows:
                    raise RuntimeError(
                        f"fail_closed:conflict_rows={result.conflict_rows}"
                    )

                self._finish_run(cur, result)
            self.connection.commit()
            return result
        except Exception as exc:
            self.connection.rollback()
            self._record_failure(result, started_at, exc)
            raise

    @staticmethod
    def _load_exact_paper_evidence(cur: Any) -> list[tuple[Any, ...]]:
        cur.execute("""
            SELECT
                i.candidate_id,
                p.id,
                p.updated_at,
                e.id,
                e.candidate_uuid,
                e.observation_uuid,
                e.strategy_code,
                e.symbol,
                e.timeframe,
                p.paper_status
            FROM analytics.paper_runtime_candidate_v1 p
            JOIN analytics.edge_candidate_v1 e
              ON e.id=p.candidate_id
             AND e.observation_uuid=p.observation_uuid
             AND e.strategy_code=p.strategy_code
             AND e.symbol=p.symbol
             AND e.timeframe=p.timeframe
            JOIN analytics.profit_factory_candidate_identity_v1 i
              ON i.edge_candidate_id=e.id
             AND i.candidate_id=e.candidate_uuid
             AND i.observation_id=e.observation_uuid
            WHERE p.observation_uuid IS NOT NULL
            ORDER BY i.candidate_id, p.id
        """)
        return list(cur.fetchall())

    def _reconcile_paper_row(
        self, cur: Any, row: tuple[Any, ...], *, dry_run: bool
    ) -> str:
        candidate_id, paper_id, observed_at, edge_id, candidate_uuid, observation_uuid, strategy, symbol, timeframe, paper_status = row
        target_id = str(paper_id)
        cur.execute("""
            SELECT verification_status, evidence_payload
            FROM analytics.profit_factory_candidate_link_v1
            WHERE candidate_id=%s
              AND target_stage='PAPER'
              AND target_entity_type='PAPER_RUNTIME_CANDIDATE'
              AND target_entity_id=%s
            FOR UPDATE
        """, (candidate_id, target_id))
        existing = cur.fetchone()

        evidence = {
            "edge_candidate_id": edge_id,
            "candidate_uuid": str(candidate_uuid),
            "observation_uuid": str(observation_uuid),
            "strategy_code": strategy,
            "symbol": symbol,
            "timeframe": timeframe,
            "paper_status": paper_status,
            "reconciliation_rule": "EDGE_ID_OBSERVATION_STRATEGY_SYMBOL_TIMEFRAME_EXACT_V1",
        }

        if existing and existing[0] in ("CONFLICT", "QUARANTINED"):
            return "CONFLICT"
        if existing and existing[0] == "VERIFIED" and existing[1] == evidence:
            return "SKIPPED"
        if dry_run:
            return "UPDATED" if existing else "CREATED"

        if existing:
            cur.execute("""
                UPDATE analytics.profit_factory_candidate_link_v1
                SET source_table='analytics.paper_runtime_candidate_v1',
                    source_record_id=%s,
                    link_method='SOURCE_REFERENCE',
                    verification_status='VERIFIED',
                    confidence_score=1,
                    evidence_payload=%s::jsonb,
                    evidence_observed_at=%s,
                    verified_at=now(),
                    verified_by=%s,
                    updated_at=now()
                WHERE candidate_id=%s
                  AND target_stage='PAPER'
                  AND target_entity_type='PAPER_RUNTIME_CANDIDATE'
                  AND target_entity_id=%s
            """, (target_id, self._json(evidence), observed_at, ENGINE_VERSION, candidate_id, target_id))
            return "UPDATED"

        cur.execute("""
            INSERT INTO analytics.profit_factory_candidate_link_v1 (
                candidate_id, target_stage, target_entity_type, target_entity_id,
                source_table, source_record_id, link_method, verification_status,
                confidence_score, evidence_payload, evidence_observed_at,
                verified_at, verified_by
            ) VALUES (
                %s, 'PAPER', 'PAPER_RUNTIME_CANDIDATE', %s,
                'analytics.paper_runtime_candidate_v1', %s,
                'SOURCE_REFERENCE', 'VERIFIED', 1, %s::jsonb, %s, now(), %s
            )
        """, (candidate_id, target_id, target_id, self._json(evidence), observed_at, ENGINE_VERSION))
        return "CREATED"

    @staticmethod
    def _load_direct_runtime_production_evidence(cur: Any) -> list[tuple[Any, ...]]:
        cur.execute("""
            SELECT candidate_id, 'PAPER', 'PAPER_HANDOFF_REFERENCE', paper_entity_id,
                   'analytics.profit_factory_runtime_handoff_v1', handoff_id::text,
                   created_at, data_scope,
                   jsonb_build_object(
                       'handoff_id', handoff_id,
                       'paper_entity_id', paper_entity_id,
                       'data_scope', data_scope
                   )
            FROM analytics.profit_factory_runtime_handoff_v1
            WHERE handoff_status='ACCEPTED'
            UNION ALL
            SELECT candidate_id, 'RUNTIME', 'RUNTIME_HANDOFF', handoff_id::text,
                   'analytics.profit_factory_runtime_handoff_v1', handoff_id::text,
                   created_at, data_scope,
                   jsonb_build_object(
                       'paper_entity_id', paper_entity_id,
                       'strategy_code', runtime_strategy_code,
                       'symbol', runtime_symbol,
                       'timeframe', runtime_timeframe,
                       'handoff_status', handoff_status,
                       'data_scope', data_scope
                   )
            FROM analytics.profit_factory_runtime_handoff_v1
            WHERE handoff_status='ACCEPTED'
            UNION ALL
            SELECT candidate_id, 'PRODUCTION', 'PRODUCTION_ALLOCATION', allocation_id::text,
                   'analytics.profit_factory_production_allocation_v1', allocation_id::text,
                   created_at, data_scope,
                   jsonb_build_object(
                       'handoff_id', handoff_id,
                       'allocation_status', allocation_status,
                       'capital_allocated', capital_allocated,
                       'currency_code', currency_code,
                       'data_scope', data_scope
                   )
            FROM analytics.profit_factory_production_allocation_v1
            WHERE allocation_status IN ('ACTIVE', 'CLOSED')
            ORDER BY 1, 2, 4
        """)
        return list(cur.fetchall())

    def _reconcile_direct_evidence(
        self, cur: Any, row: tuple[Any, ...], *, dry_run: bool
    ) -> str:
        candidate_id, stage, entity_type, entity_id, source_table, source_id, observed_at, data_scope, evidence = row
        cur.execute("""
            SELECT verification_status, evidence_payload
            FROM analytics.profit_factory_candidate_link_v1
            WHERE candidate_id=%s AND target_stage=%s
              AND target_entity_type=%s AND target_entity_id=%s
            FOR UPDATE
        """, (candidate_id, stage, entity_type, entity_id))
        existing = cur.fetchone()
        if existing and existing[0] in ("CONFLICT", "QUARANTINED"):
            return "CONFLICT"
        if existing and existing[0] == "VERIFIED" and existing[1] == evidence:
            return "SKIPPED"
        if dry_run:
            return "UPDATED" if existing else "CREATED"
        if existing:
            cur.execute("""
                UPDATE analytics.profit_factory_candidate_link_v1
                SET source_table=%s, source_record_id=%s,
                    link_method='SOURCE_REFERENCE', verification_status='VERIFIED',
                    confidence_score=1, evidence_payload=%s::jsonb,
                    evidence_observed_at=%s, verified_at=now(), verified_by=%s,
                    updated_at=now()
                WHERE candidate_id=%s AND target_stage=%s
                  AND target_entity_type=%s AND target_entity_id=%s
            """, (source_table, source_id, self._json(evidence), observed_at,
                  ENGINE_VERSION, candidate_id, stage, entity_type, entity_id))
            return "UPDATED"
        cur.execute("""
            INSERT INTO analytics.profit_factory_candidate_link_v1 (
                candidate_id, target_stage, target_entity_type, target_entity_id,
                source_table, source_record_id, link_method, verification_status,
                confidence_score, evidence_payload, evidence_observed_at,
                verified_at, verified_by
            ) VALUES (%s, %s, %s, %s, %s, %s, 'SOURCE_REFERENCE',
                      'VERIFIED', 1, %s::jsonb, %s, now(), %s)
        """, (candidate_id, stage, entity_type, entity_id, source_table,
              source_id, self._json(evidence), observed_at, ENGINE_VERSION))
        return "CREATED"

    @staticmethod
    def _json(value: dict[str, Any]) -> str:
        import json
        return json.dumps(value, sort_keys=True, default=str)

    @staticmethod
    def _start_run(cur: Any, result: ReconciliationResult, started_at: datetime) -> None:
        cur.execute("""
            INSERT INTO analytics.profit_factory_reconciliation_run_v1 (
                run_id, engine_version, mode, status, started_at
            ) VALUES (%s, %s, %s, 'RUNNING', %s)
        """, (result.run_id, ENGINE_VERSION, result.mode, started_at))

    @staticmethod
    def _finish_run(cur: Any, result: ReconciliationResult) -> None:
        cur.execute("""
            UPDATE analytics.profit_factory_reconciliation_run_v1
            SET status='COMPLETED', finished_at=now(), source_rows=%s,
                created_rows=%s, updated_rows=%s, conflict_rows=%s,
                stale_rows=%s, skipped_rows=%s
            WHERE run_id=%s
        """, (
            result.source_rows, result.created_rows, result.updated_rows,
            result.conflict_rows, result.stale_rows, result.skipped_rows,
            result.run_id,
        ))

    def _record_failure(
        self, result: ReconciliationResult, started_at: datetime, exc: Exception
    ) -> None:
        with self.connection.cursor() as cur:
            cur.execute("""
                INSERT INTO analytics.profit_factory_reconciliation_run_v1 (
                    run_id, engine_version, mode, status, started_at, finished_at,
                    source_rows, created_rows, updated_rows, conflict_rows,
                    stale_rows, skipped_rows, error_text
                ) VALUES (%s, %s, %s, 'FAILED', %s, now(), %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id) DO UPDATE SET
                    status='FAILED', finished_at=now(), error_text=EXCLUDED.error_text
            """, (
                result.run_id, ENGINE_VERSION, result.mode, started_at,
                result.source_rows, result.created_rows, result.updated_rows,
                result.conflict_rows, result.stale_rows, result.skipped_rows,
                str(exc),
            ))
        self.connection.commit()
