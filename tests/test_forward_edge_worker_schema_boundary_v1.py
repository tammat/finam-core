from pathlib import Path


WORKERS = (
    "src/scripts/run_forward_edge_observation_worker_v1.py",
    "src/scripts/run_forward_edge_relation_router_v1.py",
)


def test_runtime_workers_do_not_own_schema_changes() -> None:
    for path in WORKERS:
        source = Path(path).read_text()
        assert "ALTER TABLE" not in source
        assert "CREATE TABLE" not in source


def test_runtime_workers_release_transactions_per_candidate() -> None:
    for path in WORKERS:
        source = Path(path).read_text()
        assert source.count("conn.commit()") >= 2


def test_schema_is_owned_by_migration() -> None:
    migration = Path("sql/analytics/064_forward_edge_worker_schema_boundary_v1.sql").read_text()
    assert "ALTER TABLE analytics.forward_edge_observation_v1" in migration
    assert "CREATE TABLE IF NOT EXISTS analytics.forward_edge_worker_state_v1" in migration
