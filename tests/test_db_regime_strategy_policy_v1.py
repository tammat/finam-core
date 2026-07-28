from contextlib import contextmanager

from finam_core.strategy.db_regime_strategy_policy_v1 import (
    DbRegimeStrategyPolicyV1,
)


class _Cursor:
    def __init__(self, row):
        self.row = row
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, _sql, params):
        self.params = params

    def fetchone(self):
        return self.row


class _Connection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


class _Logger:
    def __init__(self, row):
        self.cursor = _Cursor(row)

    @contextmanager
    def _connect(self):
        yield _Connection(self.cursor)


def test_policy_is_loaded_from_database():
    logger = _Logger(
        (
            "MEAN_REVERSION_EQUITY",
            "BOTH",
            False,
            1.75,
            "DYNAMIC_EXIT_V1",
            20,
        )
    )
    policy = DbRegimeStrategyPolicyV1(logger).resolve(
        asset_group="EQUITY",
        trend="range",
        data_ready=True,
        stale=False,
    )
    assert policy is not None
    assert policy.strategy_code == "MEAN_REVERSION_EQUITY"
    assert policy.countertrend_allowed is False
    assert policy.minimum_cost_buffer == 1.75
    assert policy.exit_policy_code == "DYNAMIC_EXIT_V1"
    assert policy.max_holding_bars == 20
    assert logger.cursor.params == ("EQUITY", "range")


def test_missing_or_unconfirmed_policy_fails_closed():
    resolver = DbRegimeStrategyPolicyV1(_Logger(None))
    assert resolver.resolve(
        asset_group="EQUITY",
        trend="unknown",
        data_ready=True,
        stale=False,
    ) is None
    assert resolver.resolve(
        asset_group="EQUITY",
        trend="trend_up",
        data_ready=False,
        stale=False,
    ) is None
