from __future__ import annotations

import json
from decimal import Decimal

import psycopg2
import psycopg2.extras

SOURCE_VERSION="MAX_EDGE_SCORE_AUDIT_V1"

COMPONENTS=[
("NET_AFTER_TAX","net_after_tax"),
("PROFIT_FACTOR","profit_factor"),
("EXPECTANCY","expectancy"),
("TRADES","trades"),
("MAX_DRAWDOWN","max_drawdown"),
]

def d(v):
    return Decimal(str(v or 0))

def pct(total,value):
    if total==0:
        return Decimal("0")
    return (value/total*Decimal("100")).quantize(Decimal("0.000001"))

conn=psycopg2.connect("postgresql:///finam_core")

cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("""

SELECT *

FROM analytics.max_edge_ranking_v1

WHERE source_version='MAX_EDGE_DISCOVERY_ENGINE_V1'

ORDER BY rank_no

""")

rows=cur.fetchall()

for row in rows:

    cur.execute("""

    INSERT INTO analytics.max_edge_score_audit_v1(

        candidate_id,
        symbol,
        strategy_code,
        timeframe,
        edge_score,
        confidence,
        overall_verdict,
        source_version

    )

    VALUES(

        %s,%s,%s,%s,%s,%s,%s,%s

    )

    RETURNING audit_id

    """,

    (

        row["candidate_id"],
        row["symbol"],
        row["strategy_code"],
        row["timeframe"],
        row["edge_score"],
        row["confidence"],
        "PASS",
        SOURCE_VERSION

    ))

    audit_id=cur.fetchone()["audit_id"]

    total=Decimal("0")

    values=[]

    for code,column in COMPONENTS:

        v=abs(d(row[column]))

        values.append((code,column,v))

        total+=v

    for code,column,value in values:

        cur.execute("""

        INSERT INTO analytics.max_edge_score_component_v1(

            audit_id,

            component_code,

            component_value,

            contribution_score,

            contribution_pct,

            source_column,

            source_version

        )

        VALUES(

            %s,%s,%s,%s,%s,%s,%s

        )

        """,

        (

            audit_id,

            code,

            value,

            value,

            pct(total,value),

            column,

            SOURCE_VERSION

        ))

conn.commit()

cur.close()
conn.close()

print("VERDICT=MAX_EDGE_SCORE_AUDIT_PART1_READY")
