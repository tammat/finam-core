from finam_core.strategy.db_regime_strategy_policy_v1 import DbRegimeStrategyPolicyV1


class _Cursor:
    def __init__(self, *, row=None, error=None):
        self.row = row
        self.error = error

    def execute(self, *_args):
        if self.error:
            raise self.error

    def fetchone(self):
        return self.row

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _Connection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _Logger:
    def __init__(self, cursor):
        self.cursor = cursor

    def _connect(self):
        return _Connection(self.cursor)


def test_missing_route_is_not_reported_as_database_failure():
    repository = DbRegimeStrategyPolicyV1(_Logger(_Cursor(row=None)))
    assert repository.resolve(
        asset_group="FUTURES_GOLD", trend="range", data_ready=True, stale=False
    ) is None
    assert repository.resolution_status(
        asset_group="FUTURES_GOLD", trend="range"
    ) == "NOT_ROUTED"


def test_query_failure_remains_fail_closed_and_observable():
    repository = DbRegimeStrategyPolicyV1(
        _Logger(_Cursor(error=RuntimeError("database unavailable")))
    )
    assert repository.resolve(
        asset_group="FUTURES_GOLD", trend="trend_up", data_ready=True, stale=False
    ) is None
    assert repository.resolution_status(
        asset_group="FUTURES_GOLD", trend="trend_up"
    ) == "QUERY_FAILED"
