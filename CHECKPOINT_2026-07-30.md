# MarketCore checkpoint — 30 July 2026

## Outcome

- Paper-only Champion–Challenger workflow is implemented and persisted.
- Energy entry/exit defects that produced 1-second to 5-minute regime closes are
  corrected in code and covered by tests.
- Latest/overnight trades remain visible in HOME.
- Full and morning calibration schedules are version-controlled.
- REAL execution remains disabled; this checkpoint does not authorize micro-live.

## Verified data state

- `analytics.entry_exit_champion_challenger_v1`: 13 scoped states.
- Maximum paired sample: Brent LONG 11/80; OOS 0.
- Paper Challenger: 0; ready for Champion confirmation: 0; active Champion: 0.
- `marketcore_ui.micro_live_readiness_v1`: 20 rows, ready 0, allowed 0.
- Historical early regime exits under ten minutes: 10 total, split BR 5 / NG 5.
- `finam_core` database size is about 42 GB.

## Runtime and safety

- `finam-paper-pipeline.service` was verified active in Paper mode.
- `EXECUTION_ENABLED=0`, `REAL_TRADING_ENABLED=0`, `EXECUTION_MODE=paper`.
- Energy minimum hold is 1,800 seconds for soft time/regime exits.
- Stop-loss remains immediate; trailing broker orders remain dry-run.
- Existing real broker portfolio is read-only input and must not be imported into
  the isolated Paper or future micro-live position scope.

## Implemented controls

1. Rolling 24-hour recent-deal window and cross-midnight active positions.
2. Automatic Shadow candidate ranking with hard sample/OOS/risk guards.
3. Forward-only Paper Challenger comparison and operator-confirmed Champion
   promotion with rollback.
4. Stable futures groups (`BR`, `NG`, `CNY`) across contract changes.
5. Regime invalidation cannot bypass minimum holding time.
6. New entries reset exit state; entry fills and exit fills are distinguished.
7. NG direction requires fresh `CANDLE_REGIME_V3`, three confirmed bars and
   direction-consistent M5 slope; duplicate regime-bar entry is blocked.

## Scheduling

- Full calibration: `00:30 Europe/Moscow`, persistent, randomized delay <=120 s.
- Lightweight Champion–Challenger control: `06:15 Europe/Moscow`, persistent,
  randomized delay <=60 s.
- Unit files:
  - `deploy/systemd/finam-futures-risk-calibration.service`
  - `deploy/systemd/finam-futures-risk-calibration.timer`
  - `deploy/systemd/finam-entry-exit-control.service`
  - `deploy/systemd/finam-entry-exit-control.timer`

## Pending operator application

```bash
sudo install -m 0644 /opt/finam-core/deploy/systemd/finam-futures-risk-calibration.{service,timer} /etc/systemd/system/
sudo install -m 0644 /opt/finam-core/deploy/systemd/finam-entry-exit-control.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now finam-futures-risk-calibration.timer
sudo systemctl enable --now finam-entry-exit-control.timer
sudo systemctl restart finam-paper-pipeline.service
```

Verify:

```bash
systemctl is-active finam-paper-pipeline.service
systemctl list-timers finam-futures-risk-calibration.timer finam-entry-exit-control.timer --no-pager
```

## Micro-live readiness decision

- Overall launch readiness is approximately 30–40%; do not enable real orders.
- Required next evidence: a statistically admitted Paper Challenger, forward
  Paper comparison, active Champion, repaired V5-to-micro-live readiness mapping,
  non-dry-run protective-order canary, active position reconciliation and an
  isolated Real Canary scope with operator approval and kill-switch.

## Git checkpoint

## Evidence snapshot — 30.07.2026

- 13 Shadow states; 0 Paper Challengers; 0 Champions; 0 rollbacks.
- True forward OOS: 0. The visible 25% tail is a preliminary control reserve,
  not frozen-candidate forward evidence.
- Largest independent sample: BR LONG 9 observations, reserve 2. GAZP and NVTK
  LONG have 6 each; NG LONG 5; SBER and VTBR LONG 4 each; other states 1–3.
- No edge is statistically confirmed. BR/NVTK/SBER LONG are early research leads;
  GAZP/NG LONG require entry-quality diagnosis.
- Freeze the bounded parameter space and collect new independent signals. Do not
  enable REAL and do not weaken gates merely to accelerate promotion.

## Automatic Paper lifecycle (fixed)

1. Intraday Shadow admission is adaptive: standard promotion requires 60/15,
   five active days and two regimes. A broad 10-day/three-regime history may
   enter Challenger at 40/10, but still must pass the separate 30/10 forward
   comparison before Champion. Repeated same-direction signals within 30 minutes
   count once. A provisional chronological 25% OOS reserve is shown from the
   first observations but cannot promote a candidate on its own.
2. Paper Challenger: 30 new paired trades, including 10 OOS, and expectancy gain
   of at least +0.05R versus the current Paper Champion.
3. Champion: promoted automatically in Paper only; REAL remains disabled.
4. Soft rollback: after 20 new trades, expectancy <= -0.10R or PF < 0.80 in two
   consecutive daily cycles.
5. Emergency rollback: after 10 trades, drawdown above max(3R, 1.25 times the
   validated drawdown); the previous Paper profile is restored immediately.
6. UI shows status, progress, health and reasons; lifecycle action buttons are not
   part of the automatic workflow.

- Branch: `codex/research-edge-v5`.
- Functional commits included: `2d0abff0`, `ecbb5d0d`, `85ab2214`, `fb6911ce`,
  `3afea16d`, `b660c878`, `c911219b`.
- Checkpoint: V5 purged OOS isolation is installed. Admissions freeze their V5
  boundary, apply a holding-horizon embargo, and route only future observations
  into an idempotent audited worker scheduled every 15 minutes.
- Reuse protection V2: a trade is unique inside each OOS run, while every
  hypothesis registered before its entry may evaluate the same future event.
  This removes candidate-order bias without allowing train/OOS reuse.
- Training protection: active OOS boundaries are excluded from the V5 training
  view, preventing feedback of validation outcomes into evidence selection.
- Research split protection: active intraday, momentum, relationship,
  intermarket, generic walk-forward and Swing validation paths use purged
  boundaries based on the candidate label horizon.
- Operational truth at checkpoint: V5 closed trades 56; exact V5 contexts 42;
  OOS admissions waiting for fresh data 23; V5 OOS runs 0; OOS PASS 0;
  automatic REAL promotion is absent and REAL trading remains disabled.
- Debt-closure checkpoint: V5 OOS input is physically restricted to Paper V5,
  frozen cost admission V2 is active, exact-context training freeze is installed,
  historical pre-purging results are quarantined from promotion, and all known
  active plus legacy temporal splits have an explicit purging/embargo contract.
- Transactional DB integration test passed without persistent synthetic rows:
  production `v5_oos_run_v1=0`, audit observations `=0` after rollback.
- Tests at this checkpoint: 67 passed. All primary services remained active;
  no orders, fills, Paper profiles or REAL permissions were changed.

## V5 methodology integrity V2

- Cohorts use only the entry-time `planned_exit_rule`; the realized exit reason
  is outcome/audit metadata and cannot affect selection.
- Admission and hierarchical evidence include a conservative two-tick
  spread/slippage floor in addition to recorded execution costs and fail closed
  when the contract cost specification is missing.
- OOS stores raw and effective observation counts. Same-day correlated positions
  are collapsed into an asset-event cluster before expectancy and PF are tested.
- Global first-writer trade claiming is disabled; only preregistered hypotheses
  can share a subsequent event, with uniqueness retained inside a run.
- Recalculated production state: 56 V5 trades, 39 exact entry-time contexts,
  39 cost guards waiting for sample, 0 OOS runs and 0 OOS PASS. REAL is disabled.
- Migration: `234_v5_methodology_integrity_v2.sql`. Focused validation: 43 passed.

## MX/RVI Shadow expansion

- `MXU6@RTSX`: isolated LONG/SHORT M5 Shadow observer with completed-bar-only
  20-bar breakout and entry-time ATR risk. No Paper/REAL permission.
- `VIU6@RTSX`: RVI regime input only; non-tradable, with LOW/NORMAL/HIGH rolling
  percentile states. Initial load: 470 M1 bars; latest state LOW_VOL at RVI 41.6.
- Frozen forward baseline remains immutable; the defective legacy MX proxy job is
  disabled and replaced by a separate Shadow table and governed observer.
- Migrations: `235_mx_index_shadow_onboarding_v1.sql`,
  `236_rvi_shadow_feature_onboarding_v1.sql`. Focused tests: 14 passed.

## Market regime context V1

- Completed MX/RVI bars are frozen into `market_regime_context_v1` before a
  signal can consume them; post-entry context cannot rewrite the snapshot.
- Three paired Shadow variants are stored per parent signal: baseline, MX-only
  and MX+RVI. Decisions and risk multipliers remain advisory and cannot trade.
- Initial state: MX UP / RVI LOW_VOL / RISK_ON; 66 variants for 22 source signals.
- Control UI includes regime cards and recent Shadow variants. Migration:
  `237_market_regime_context_v1.sql`; renderer/resolver integration passed.

## Market regime integrity V2

- Market context is now causal: completed MX M5 is derived from M1 and RVI must
  have completed before the context timestamp. Freshness is persisted explicitly.
- Stale RVI degrades only the MX+RVI Shadow variant (`RVI_STALE`); stale MX blocks
  the context. Only accepted/filled `FRESH_V5` Paper entries can be observed.
- Shadow variants now have auditable close-only outcomes and net P&L after a
  conservative two-tick execution cost. They cannot place or modify orders.
- Contaminated baseline archived in cleanup audit: 1 context and 66 variants;
  valid V2 collection restarted at zero.
- Scheduler priority is RVI 60, context V2 61, MX observer 62. Latest verified
  V2 context was causal and fresh at 10:45 MSK. Focused tests: 19 passed.
## Trend-aware Paper hard max hold

- All Paper asset classes have explicit nominal/absolute holding limits. A fresh
  favorable trend may extend only from nominal to 2x; the absolute limit closes
  unconditionally. Stop, target, trailing and adverse regime remain higher priority.
- UI reasons are Russian and Paper/Shadow parameters are separated truthfully.
  No optimized Paper runtime profile existed at checkpoint; strategy defaults
  remain active. REAL was not changed. Exit tests: 17; direct UI render passed.
