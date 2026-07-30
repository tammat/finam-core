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

- Branch: `codex/research-edge-v5`.
- Functional commits included: `2d0abff0`, `ecbb5d0d`, `85ab2214`, `fb6911ce`.
