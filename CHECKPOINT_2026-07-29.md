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
## Multi-futures adaptive policy addendum — 20:41 MSK

- New module: `src/finam_core/strategy/futures_adaptive_risk_policy.py`.
- Paper integration occurs on the common intent path before signal persistence and execution.
- Modes: BR=ENFORCE; NG/USD/CNY/GOLD=SHADOW; all are configurable per asset by `FUTURES_ADAPTIVE_<ASSET>_MODE`.
- Tests passed for all five assets in LONG and SHORT, ATR bounds, reward/risk, volume rejection, 3x cost-buffer rejection and risk-normalized sizing.
- Runtime evidence: CNY SHADOW 1.2/2.0 ATR; BR ENFORCE 1.8/2.7 ATR; NG SHADOW 1.5/3.0 ATR with qty 0.533333.
- Service verified active with PID 3877920; no Traceback, ImportError or SyntaxError after restart.
- Promotion rule: do not move NG/USD/CNY/GOLD from SHADOW to ENFORCE before sufficient closed Paper evidence and MAE/MFE review.
## Daily futures calibrator addendum — 20:58 MSK

- New analytics module: `src/finam_core/analytics/futures_risk_calibrator.py`.
- New job: `src/scripts/analytics/build_futures_risk_calibration_v1.py`.
- New storage: `analytics.futures_risk_calibration_v1` from migration 224.
- New units: `finam-futures-risk-calibration.service/.timer`, scheduled daily at 21:15 MSK.
- Trusted cohort only: Paper + FRESH_V5; legacy data rejected after the initial data-quality audit exposed an invalid USD MAE of 3351 ATR.
- No automatic parameter mutation. Output states are `INSUFFICIENT_DATA`, `ADVISORY_READY`, and `CANDIDATE_FOR_REVIEW`.
- First trusted calculation persisted 10 asset/side rows; all are insufficient and therefore contain no recommendation.
- Tests: 2 passed; database calculation and upsert verified.
- Pending operator action: install the two unit files under `/etc/systemd/system`, daemon-reload, enable/start the timer.
## Shadow-to-Paper automation addendum — 21:12 MSK

- New module: `src/finam_core/analytics/futures_shadow_promotion.py`.
- New daily stage: `src/scripts/analytics/build_futures_shadow_promotion_v1.py` runs after calibration.
- New storage migration 225: paired Shadow outcomes and versioned Paper runtime profiles.
- Auto-promotion boundary is PAPER only; REAL cannot be activated by this job.
- V5 integrity: Shadow rows are external to `closed_trades`; actual Paper closes retain normal V5 counting and carry `risk_profile_version` for cohort attribution.
- Promotion is reversible: previous ACTIVE version becomes SUPERSEDED, historical pairs and versions remain immutable/auditable.
- First cycle persisted paired evidence but promoted nothing because minimum sample/OOS guards failed.
- Pending operator actions: replace the installed calibration service with the repository version, daemon-reload, restart timer; restart Paper once to load runtime-profile lookup code.

## Runtime/UI checkpoint — 22:50 MSK

- Verified services: `finam-paper-pipeline`, `marketcore-ui-shell`, and `finam-paper-safe` are active; the UI listens on internal port `8080` and is published externally on `18080`.
- Verified safety: Paper only (`EXECUTION_MODE=paper`); execution and real-trading flags remain `0`.
- HOME cold rendering was reduced to approximately `0.09–0.15 s` in a fresh process and approximately `0.006 s` from cache by replacing the tick-level floating-P&L lookup with indexed latest-bar lookup.
- The governed optimizer actions are implemented and committed: confirm Paper, reject, continue Shadow, and rollback. Readiness/OOS gates remain mandatory; no action can promote to REAL.
- A clearer card-based optimizer presentation is preserved as an undeployed local draft (`.codex-tmp/renderer_clarity.py`, `.codex-tmp/css_clarity.css`). It must be validated before deployment; the currently deployed flat button grid remains functionally correct but visually unclear.
- NG entry admission is fail-closed. After the pipeline restart, runtime emitted `NG_RUNTIME_UNIVERSE_DISABLED enabled=NONE`; no new NG entry signals were generated. Existing-position EXIT handling remains available.
- Liquidity evidence favors `NGQ6` over `NGU6` (M1 volume 457901 vs 51205), but `NGQ6` is still blocked by governance. Do not bypass this state by directly editing the enabled flag.
- Branch checkpoint before this documentation commit: `codex/research-edge-v5` at `e230bbdb`, synchronized with origin.

### Resume order

1. Inspect `ng_live_runtime_state` and the state-machine/governance reason for `active_edge=false`.
2. Select exactly one canonical NG contract through the governed state transition; keep entries blocked if the transition cannot pass.
3. Deploy and test the card-based optimizer UI on desktop and mobile.
4. Reconfirm Paper/REAL safety flags and save new runtime evidence.
