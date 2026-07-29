# MarketCore checkpoint — 29 July 2026, 15:15 MSK

## Verified runtime state

- Execution mode: Paper only. Real trading and LIVE execution are disabled.
- Market data: 16 enabled M5 instruments; freshness recovered.
- V5 totals are aggregated by symbol and direction and daily growth is visible.
- CNY: a valid trend-up retest passed cost/data gates and produced a Paper entry at
  14:00:36 MSK after the database privilege repair.
- UI: separate collapsible/sortable Equity and Futures tables; Russian labels;
  active/closed semantics; signed RUB mark-to-market in the active exit column and
  green/pink P&L color coding.
- XRDP is disabled and port 3389 is closed. UI uses internal 8080/external 18080.

## Safety decisions

- Protective stop-loss, take-profit and hard TIME_EXIT remain autonomous.
- Stall-exit is not accepted as a proven edge and is prepared for removal from
  Paper while remaining available for research/Shadow evaluation.
- BR/NG trailing support is bidirectional but remains dry-run Paper only.

## Next work

1. Implement `RANGE_BOUNDARY_SHADOW_V1` for `range_low_vol` only with confirmed
   boundaries, midpoint/opposite-bound targets, ATR-buffered stop and cost gate.
2. Implement operator review at soft TIME_EXIT and automatic hard fail-safe close.
3. Add audited Paper-only close/partial-close/stop/take commands before UI controls.
4. Optimize active mark-to-market and reconcile the persisted Paper projection.

## Acceptance evidence

- Changed Python modules compile successfully.
- BR LONG/SHORT trailing monotonic-movement smoke check passed.
- HOME API exposes RUB tables, active state and aggregated V5 counters; UI service
  is active on port 8080.
## Recovery addendum — 18:10 MSK

- `finam-paper-pipeline.service`: `active`, non-zero PID; full 12,271-line pipeline restored and compiled.
- `TIME_EXIT`: Paper-only operator confirmation gate implemented. No symbol is approved by default.
- UI renderer error `unexpected keyword argument status` corrected to `state=RenderNodeStateV2(...)`.
- `/api/v2/domain-render-tree/home` verified in a fresh process: HTTP 200.
- UI progress is top-5; active rows are highlighted; Back/Home controls are hidden.
- Pending operator action: restart `marketcore-ui-shell.service` to load the corrected Python module.
## Adaptive Brent Paper addendum — 20:33 MSK

- Scope: PAPER only, LONG and SHORT; REAL unchanged.
- Stop: structural breakout boundary plus 0.25 ATR buffer, constrained to 1.8–2.5 ATR.
- Take profit: max(regime target, 1.5R), with regime target no lower than 2.5 ATR.
- Volume gate: current M5 volume must be >= 1.3x median of 20 prior positive-volume M5 bars.
- Smoke tests passed for low-volume rejection and confirmed-volume LONG geometry; SHORT uses mirrored geometry.
- Runtime verified after restart: service active, PID 3840830, start 20:31:43 MSK, no startup traceback.
