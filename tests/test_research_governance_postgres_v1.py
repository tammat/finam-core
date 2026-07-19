import psycopg2
import psycopg2.extras


def test_governance_schema_and_cycle_order_on_postgres() -> None:
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""SELECT executor_code,step_order
                FROM analytics.edge_search_scenario_step_v1
                WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH'
                  AND executor_code IN ('AUDIT_PNL_UNITS','SYNC_ECONOMIC_HYPOTHESES',
                                        'WALKFORWARD','GOVERN_EXPERIMENTS','METHODOLOGY_GATE')""")
            order = {row["executor_code"]: int(row["step_order"]) for row in cursor.fetchall()}
            assert order["AUDIT_PNL_UNITS"] < order["WALKFORWARD"]
            assert order["SYNC_ECONOMIC_HYPOTHESES"] < order["WALKFORWARD"]
            assert order["WALKFORWARD"] < order["GOVERN_EXPERIMENTS"] < order["METHODOLOGY_GATE"]
            cursor.execute("""SELECT asset_scope,count(*) count
                FROM analytics.edge_economic_hypothesis_contract_v1
                WHERE enabled GROUP BY asset_scope""")
            scopes = {row["asset_scope"]: int(row["count"]) for row in cursor.fetchall()}
            assert scopes["EQUITY"] >= 1
            assert scopes["FUTURES"] >= 1
            cursor.execute("""SELECT count(*) count FROM presentation.ui_resource_v1
                WHERE locale_code='ru' AND resource_key IN
                ('research.tile.global_trials','research.tile.holdout','research.tile.pnl_units',
                 'research.tile.equities','research.tile.futures','research.tile.portfolio')""")
            assert int(cursor.fetchone()["count"]) == 6
