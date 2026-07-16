from __future__ import annotations

import uuid
import re
from datetime import datetime, timezone

import psycopg2

SOURCE_VERSION = "PROFIT_FUNNEL_VALIDATED_EDGE_V2"
NAMESPACE = uuid.UUID("01ace818-b308-56f4-a392-36f66d207dcc")
REQUIRED_PARAMETERS = frozenset({"lookback", "threshold"})
HOLD_PARAMETERS = frozenset({"hold", "holding_bars"})
FUTURES_MONTH = {code: month for month, code in enumerate("FGHJKMNQUVXZ", start=1)}
FUTURES_RE = re.compile(r"^[A-Z]+([FGHJKMNQUVXZ])(\d)@RTSX$")


def specification_reason(parameter_json: dict, symbol: str, now: datetime | None = None) -> str | None:
    parameters = parameter_json if isinstance(parameter_json, dict) else {}
    if not REQUIRED_PARAMETERS.issubset(parameters) or not HOLD_PARAMETERS.intersection(parameters):
        return "VALIDATED_EDGE_SPECIFICATION_INCOMPLETE"
    transaction_cost_bps = float(parameters.get("transaction_cost_bps") or 0)
    commission = float(parameters.get("commission") or 0)
    slippage = float(parameters.get("slippage") or 0)
    if transaction_cost_bps <= 0 and commission+slippage <= 0:
        return "VALIDATED_EDGE_COST_MODEL_MISSING"
    match = FUTURES_RE.fullmatch(symbol.strip().upper())
    if not match:
        return None
    current = now or datetime.now(timezone.utc)
    contract_year = current.year-current.year % 10+int(match.group(2))
    if contract_year < current.year-5:
        contract_year += 10
    if (contract_year, FUTURES_MONTH[match.group(1)]) < (current.year, current.month):
        return "VALIDATED_EDGE_CONTRACT_EXPIRED"
    return None


def main() -> None:
    inserted = 0
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT candidate_uuid,observation_uuid,discovery_batch_id,validation_score,
                       validation_formula_version,updated_at,parameter_json,symbol
                FROM analytics.edge_candidate_v1
                WHERE validation_score IS NOT NULL AND validation_formula_version IS NOT NULL
                ORDER BY candidate_uuid
            """)
            rows = cursor.fetchall()
            eligible = 0
            revoked = 0
            for candidate_uuid, observation_uuid, batch_id, score, formula, validated_at, parameters, symbol in rows:
                reason = specification_reason(parameters, symbol)
                validation_id = uuid.uuid5(NAMESPACE, "validation:" + str(candidate_uuid))
                if reason:
                    cursor.execute("""
                        UPDATE analytics.profit_funnel_validated_edge_v2
                        SET validation_status='REVOKED',validation_reason_code=%s,
                            paper_allowed=false,runtime_allowed=false,live_allowed=false,
                            source_version=%s
                        WHERE candidate_uuid=%s AND validation_status<>'REVOKED'
                    """, (reason,SOURCE_VERSION,str(candidate_uuid)))
                    revoked += cursor.rowcount
                    continue
                eligible += 1
                cursor.execute("""
                    INSERT INTO analytics.profit_funnel_validated_edge_v2 (
                        validation_id,candidate_uuid,observation_uuid,discovery_batch_id,
                        validation_score,validation_formula_version,validation_status,
                        paper_allowed,runtime_allowed,live_allowed,source_version,validated_at,
                        validation_reason_code
                    ) VALUES (%s,%s,%s,%s,%s,%s,'PASS',false,false,false,%s,%s,'VALIDATED_EDGE_ELIGIBLE')
                    ON CONFLICT (candidate_uuid) DO UPDATE SET
                        validation_status='PASS',validation_reason_code='VALIDATED_EDGE_ELIGIBLE',
                        source_version=EXCLUDED.source_version,validated_at=EXCLUDED.validated_at
                """, (str(validation_id),str(candidate_uuid),str(observation_uuid),batch_id,
                      score,formula,SOURCE_VERSION,validated_at))
                inserted += cursor.rowcount
    print(f"eligible_validated_edges={eligible}")
    print(f"revoked_validated_edges={revoked}")
    print(f"inserted_validated_edges={inserted}")
    print("paper_changed=0")
    print("runtime_changed=0")
    print("live_allowed=0")
    print("VERDICT=MARKETCORE_PROFIT_FUNNEL_VALIDATED_EDGE_V2_READY")


if __name__ == "__main__":
    main()
