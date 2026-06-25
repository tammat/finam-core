#!/usr/bin/env python3

import os
import psycopg2
from psycopg2.extras import Json


CANDIDATE_ID = "MSC-000001"


def main() -> int:
    print("=== RESEARCH_KNOWLEDGE_BASE_SEED_MSC000001_V1 ===")
    print("mode=seed_apply")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("orders_sent=0")

    db = os.environ.get("DATABASE_URL", "")
    if not db:
        print("db_update=0")
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2
    if db.startswith("sqlite"):
        print("db_update=0")
        print("ERROR=SQLITE_FORBIDDEN")
        return 2

    payload = {
        "instrument_signature": "MS-A51761DAAE2F",
        "fx_signature": "MS-B3C22849CB56",
        "energy_signature": "MS-A51761DAAE2F",
        "robustness": "WEAK",
        "rejection_detail": "72_of_77_trades_clustered_on_one_day",
        "source_checkpoints": [
            "checkpoint_market_state_context_scorecard_v1",
            "checkpoint_market_state_context_edge_decision_v1",
            "checkpoint_market_state_context_candidate_audit_v1",
            "checkpoint_market_state_context_robustness_check_v1",
        ],
    }

    with psycopg2.connect(db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO research.research_candidates_v1 (
                    candidate_id,
                    candidate_version,
                    candidate_type,
                    instrument_signature,
                    fx_signature,
                    energy_signature,
                    session_signature,
                    symbol,
                    strategy,
                    timeframe,
                    trade_count,
                    winrate,
                    expectancy,
                    profit_factor,
                    net_pnl,
                    commission,
                    max_drawdown,
                    validation_level,
                    status,
                    status_reason,
                    discovered_at,
                    last_validation_at,
                    created_by_script,
                    payload
                )
                VALUES (
                    %s,1,%s,%s,%s,%s,NULL,
                    NULL,NULL,NULL,
                    77,0.4675,1.912857,1.942233,147.290019,NULL,NULL,
                    %s,%s,%s,
                    now(),now(),
                    %s,%s
                )
                ON CONFLICT(candidate_id)
                DO UPDATE SET
                    trade_count=EXCLUDED.trade_count,
                    winrate=EXCLUDED.winrate,
                    expectancy=EXCLUDED.expectancy,
                    profit_factor=EXCLUDED.profit_factor,
                    net_pnl=EXCLUDED.net_pnl,
                    validation_level=EXCLUDED.validation_level,
                    status=EXCLUDED.status,
                    status_reason=EXCLUDED.status_reason,
                    last_validation_at=now(),
                    payload=EXCLUDED.payload;
                """,
                (
                    CANDIDATE_ID,
                    "MARKET_STATE_CONTEXT",
                    "MS-A51761DAAE2F",
                    "MS-B3C22849CB56",
                    "MS-A51761DAAE2F",
                    "ROBUSTNESS_CHECK_V1",
                    "REJECTED",
                    "ROBUSTNESS_WEAK",
                    "seed_research_knowledge_base_msc000001_v1.py",
                    Json(payload),
                ),
            )

            cur.execute(
                """
                INSERT INTO research.research_candidate_decisions_v1 (
                    candidate_id,
                    old_status,
                    new_status,
                    decision_reason,
                    decision_detail,
                    decided_by_script,
                    payload
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s);
                """,
                (
                    CANDIDATE_ID,
                    "UNDER_RESEARCH",
                    "REJECTED",
                    "ROBUSTNESS_WEAK",
                    "72 из 77 сделок пришлись на один торговый день; кандидат не допускается к Micro Live.",
                    "seed_research_knowledge_base_msc000001_v1.py",
                    Json(payload),
                ),
            )

            cur.execute(
                """
                INSERT INTO research.research_hypotheses_v1 (
                    hypothesis_code,
                    hypothesis_type,
                    hypothesis_text_ru,
                    status,
                    status_reason,
                    linked_candidate_id,
                    payload,
                    created_by_script
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(hypothesis_code)
                DO UPDATE SET
                    status=EXCLUDED.status,
                    status_reason=EXCLUDED.status_reason,
                    payload=EXCLUDED.payload;
                """,
                (
                    "HYP-MSC-000001",
                    "MARKET_STATE_CONTEXT_EDGE",
                    "Комбинация состояния инструмента MS-A51761DAAE2F, FX-контекста MS-B3C22849CB56 и energy-контекста MS-A51761DAAE2F показала положительный PnL, но результат сконцентрирован в одном торговом дне.",
                    "REJECTED",
                    "ROBUSTNESS_WEAK",
                    CANDIDATE_ID,
                    Json(payload),
                    "seed_research_knowledge_base_msc000001_v1.py",
                ),
            )

            cur.execute(
                """
                INSERT INTO research.research_knowledge_events_v1 (
                    event_type,
                    object_type,
                    object_id,
                    event_summary_ru,
                    payload,
                    created_by_script
                )
                VALUES (%s,%s,%s,%s,%s,%s);
                """,
                (
                    "CANDIDATE_REJECTED",
                    "research_candidate",
                    CANDIDATE_ID,
                    "MSC-000001 отклонен: robustness weak, 72 из 77 сделок пришлись на один торговый день.",
                    Json(payload),
                    "seed_research_knowledge_base_msc000001_v1.py",
                ),
            )

        conn.commit()

    print(f"candidate_id={CANDIDATE_ID}")
    print("status=REJECTED")
    print("status_reason=ROBUSTNESS_WEAK")
    print("db_update=1")
    print("VERDICT=RESEARCH_KNOWLEDGE_BASE_SEED_MSC000001_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
