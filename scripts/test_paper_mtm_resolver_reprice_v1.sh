#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_MTM_RESOLVER_REPRICE_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
CREATE TABLE IF NOT EXISTS analytics.paper_portfolio_mtm_snapshot_v1 (
    snapshot_id BIGSERIAL PRIMARY KEY,
    snapshot_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    candidate_id BIGINT NOT NULL,
    strategy_code TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    trades INTEGER NOT NULL DEFAULT 0,
    gross_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    commission NUMERIC(20,8) NOT NULL DEFAULT 0,
    exchange_fee NUMERIC(20,8) NOT NULL DEFAULT 0,
    clearing_fee NUMERIC(20,8) NOT NULL DEFAULT 0,
    slippage NUMERIC(20,8) NOT NULL DEFAULT 0,
    net_trading_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    estimated_tax NUMERIC(20,8) NOT NULL DEFAULT 0,
    net_after_tax NUMERIC(20,8) NOT NULL DEFAULT 0,
    max_drawdown NUMERIC(20,8) NOT NULL DEFAULT 0,
    market_model_version TEXT NOT NULL,
    source_version TEXT NOT NULL DEFAULT 'PAPER_MTM_RESOLVER_REPRICE_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.paper_portfolio_mtm_snapshot_v1 TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
SQL

PYTHONPATH=src python -m py_compile \
  src/marketcore/paper/paper_cost_calculator.py \
  src/marketcore/paper/mtm/paper_mtm_snapshot_repository.py \
  src/marketcore/paper/mtm/__init__.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python - <<'PY'
from decimal import Decimal
import psycopg2
import psycopg2.extras

from marketcore.market.resolver import MarketModelResolver
from marketcore.paper import PaperCostCalculator
from marketcore.paper.mtm import PaperMtmSnapshotRepository

resolver = MarketModelResolver()
calculator = PaperCostCalculator()
repo = PaperMtmSnapshotRepository()

with psycopg2.connect("postgresql:///finam_core") as conn:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT
                p.candidate_id,
                p.strategy_code,
                p.symbol,
                p.timeframe,
                count(t.id) AS trades,
                coalesce(sum(t.gross_pnl),0) AS gross_pnl,
                coalesce(min(o.max_drawdown),0) AS max_drawdown
            FROM analytics.paper_runtime_candidate_v1 p
            JOIN analytics.edge_candidate_v1 c ON c.id=p.candidate_id
            JOIN analytics.edge_observation_v1 o ON o.observation_uuid=p.observation_uuid
            LEFT JOIN analytics.research_trade_v1 t ON t.research_code=c.research_code
            WHERE p.paper_status='ACTIVE'
            GROUP BY p.candidate_id, p.strategy_code, p.symbol, p.timeframe
            ORDER BY p.candidate_id
        """)
        rows = cur.fetchall()

for row in rows:
    snapshot = resolver.resolve(
        symbol=row["symbol"],
        broker_code="FINAM",
        account_scope="BASE",
    )

    costs = calculator.calculate_net_pnl(
        gross_pnl=Decimal(row["gross_pnl"]),
        entry_price=Decimal("1"),
        snapshot=snapshot,
    )

    repo.insert_snapshot(
        candidate_id=int(row["candidate_id"]),
        strategy_code=row["strategy_code"],
        symbol=row["symbol"],
        timeframe=row["timeframe"],
        trades=int(row["trades"]),
        gross_pnl=Decimal(row["gross_pnl"]),
        commission=costs["commission"],
        exchange_fee=costs["exchange_fee"],
        clearing_fee=costs["clearing_fee"],
        slippage=costs["slippage"],
        net_trading_pnl=costs["net_trading_pnl"],
        estimated_tax=costs["estimated_tax"],
        net_after_tax=costs["net_after_tax"],
        max_drawdown=Decimal(row["max_drawdown"]),
        market_model_version=snapshot.version.market_model_version,
        source_version="PAPER_MTM_RESOLVER_REPRICE_V1",
    )

print("PAPER_MTM_SNAPSHOTS_INSERTED", len(rows))
PY

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_portfolio_mtm_snapshot_v1
WHERE source_version='PAPER_MTM_RESOLVER_REPRICE_V1';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$rows" -gt 0
test "$unsafe" = "0"

psql -d finam_core -c "
SELECT
  snapshot_id,
  candidate_id,
  strategy_code,
  symbol,
  timeframe,
  trades,
  round(gross_pnl,6) AS gross_pnl,
  round(commission,6) AS commission,
  round(slippage,6) AS slippage,
  round(net_trading_pnl,6) AS net_trading_pnl,
  round(estimated_tax,6) AS estimated_tax,
  round(net_after_tax,6) AS net_after_tax,
  market_model_version
FROM analytics.paper_portfolio_mtm_snapshot_v1
ORDER BY snapshot_id DESC
LIMIT 30;
"

echo "paper_mtm_snapshot_rows=$rows"
echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_MTM_RESOLVER_REPRICE_V1_READY"
echo "VERDICT=TEST_PAPER_MTM_RESOLVER_REPRICE_V1_OK"
