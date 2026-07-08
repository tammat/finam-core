from __future__ import annotations

import json
import math
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "MARKET_CONTEXT_CORRELATION_COLLECTOR_V1"


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(Decimal(str(value)))
    except Exception:
        return None


def _returns(rows: list[dict[str, Any]]) -> dict[Any, float]:
    ordered = list(reversed(rows))
    result: dict[Any, float] = {}

    for prev, curr in zip(ordered, ordered[1:]):
        prev_close = _to_float(prev.get("close"))
        curr_close = _to_float(curr.get("close"))
        if prev_close is None or curr_close is None or prev_close == 0:
            continue
        result[curr.get("ts")] = (curr_close - prev_close) / prev_close

    return result


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None

    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)

    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)

    if vx <= 0 or vy <= 0:
        return None

    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    value = cov / math.sqrt(vx * vy)

    if value > 1:
        return 1.0
    if value < -1:
        return -1.0
    return value


def _load_bars(cur, symbol: str, timeframe: str, limit_rows: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT ts, close
        FROM public.market_bars
        WHERE symbol=%s
          AND timeframe=%s
          AND close IS NOT NULL
        ORDER BY ts DESC
        LIMIT %s
        """,
        (symbol, timeframe, limit_rows),
    )
    return list(cur.fetchall())


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT rule_code, relation_type, timeframe, lookback_bars,
                       min_observations, min_abs_correlation
                FROM knowledge.correlation_rule_v1
                WHERE is_active
                ORDER BY rule_code
                """
            )
            rules = list(cur.fetchall())

            evaluated = 0
            stored = 0
            context_symbols: set[tuple[str, str]] = set()

            for rule in rules:
                cur.execute(
                    """
                    SELECT source_symbol, target_symbol, timeframe
                    FROM knowledge.correlation_universe_v1
                    WHERE is_active
                      AND timeframe=%s
                    ORDER BY source_symbol, target_symbol
                    """,
                    (rule["timeframe"],),
                )
                pairs = list(cur.fetchall())

                for pair in pairs:
                    source_symbol = pair["source_symbol"]
                    target_symbol = pair["target_symbol"]
                    timeframe = pair["timeframe"]

                    limit_rows = int(rule["lookback_bars"]) + 1
                    source_bars = _load_bars(cur, source_symbol, timeframe, limit_rows)
                    target_bars = _load_bars(cur, target_symbol, timeframe, limit_rows)

                    source_returns = _returns(source_bars)
                    target_returns = _returns(target_bars)

                    common_ts = sorted(set(source_returns) & set(target_returns))
                    xs = [source_returns[ts] for ts in common_ts]
                    ys = [target_returns[ts] for ts in common_ts]

                    observations = len(xs)
                    if observations < int(rule["min_observations"]):
                        continue

                    corr = _pearson(xs, ys)
                    if corr is None:
                        continue

                    evaluated += 1
                    context_symbols.add((source_symbol, timeframe))
                    context_symbols.add((target_symbol, timeframe))

                    if abs(corr) < float(rule["min_abs_correlation"]):
                        continue

                    evidence = {
                        "rule_code": rule["rule_code"],
                        "timeframe": timeframe,
                        "lookback_bars": int(rule["lookback_bars"]),
                        "observations": observations,
                        "min_abs_correlation": str(rule["min_abs_correlation"]),
                        "collector_mode": "configured_universe_from_postgres",
                    }

                    cur.execute(
                        """
                        INSERT INTO knowledge.relationship_v1
                        (
                            source_type,
                            source_code,
                            relation_type,
                            target_type,
                            target_code,
                            weight,
                            confidence,
                            evidence_json,
                            is_active,
                            source_version
                        )
                        VALUES
                        (
                            'INSTRUMENT',
                            %s,
                            %s,
                            'INSTRUMENT',
                            %s,
                            %s,
                            %s,
                            %s::jsonb,
                            TRUE,
                            %s
                        )
                        ON CONFLICT
                        (source_type, source_code, relation_type, target_type, target_code, source_version)
                        WHERE source_version='MARKET_CONTEXT_CORRELATION_COLLECTOR_V1'
                        DO UPDATE SET
                            weight=EXCLUDED.weight,
                            confidence=EXCLUDED.confidence,
                            evidence_json=EXCLUDED.evidence_json,
                            is_active=TRUE,
                            created_at=now()
                        """,
                        (
                            source_symbol,
                            rule["relation_type"],
                            target_symbol,
                            corr,
                            abs(corr),
                            json.dumps(evidence, ensure_ascii=False),
                            SOURCE_VERSION,
                        ),
                    )
                    stored += 1

            for symbol, timeframe in context_symbols:
                cur.execute(
                    """
                    UPDATE knowledge.market_context_v1
                    SET correlation_state='EVALUATED'
                    WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1'
                      AND symbol=%s
                      AND timeframe=%s
                    """,
                    (symbol, timeframe),
                )

    print("=== MARKET_CONTEXT_CORRELATION_COLLECTOR_V1 ===")
    print(f"rules_loaded={len(rules)}")
    print(f"pairs_evaluated={evaluated}")
    print(f"relationships_stored={stored}")
    print(f"context_symbols_updated={len(context_symbols)}")
    print("config_source=postgres")
    print("symbol_hardcode=0")
    print("threshold_hardcode=0")
    print("edge_score_v2_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKET_CONTEXT_CORRELATION_COLLECTOR_V1_READY")


if __name__ == "__main__":
    main()
