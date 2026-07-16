# MarketCore Stage 9 rollback V2

Stage 9 switches the root workspace and canonical container navigation to Runtime V2 and makes legacy presentation URLs return HTTP 410. It does not enable real trading or change order permissions.

Rollback point: the Git commit immediately before the Stage 9 delivery (Stage 8 commit `fe4bd115`).

Rollback procedure requires explicit operator approval:

1. restore only the Stage 9 commit with `git revert`;
2. restart `marketcore-ui-shell.service`;
3. run the Stage 8 exit gate and verify that no real exchange order exists;
4. preserve the failed Stage 9 logs and audit evidence.

Do not roll back database migrations or analytics changes: Stage 9 has none.
