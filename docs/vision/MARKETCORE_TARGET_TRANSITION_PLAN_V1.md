# MARKETCORE TARGET TRANSITION PLAN V1

Version: 1.0
Status: LOCKED
Date: 2026-07-15

## 1. Purpose

This document defines the mandatory sequence for moving MarketCore to the target architecture.

North Star: maximize sustainable profit under controlled risk.

The plan is subordinate to:

1. `MARKETCORE_FINAL_ARCHITECTURE_V1`;
2. `MARKETCORE_MUST_HAVE_V1`;
3. locked architectural principles and approved ADRs.

If this plan conflicts with a higher-priority locked contract, the higher-priority contract wins and the conflict must be documented before work continues.

## 2. Execution Rules

- Stages are completed strictly in the order defined below.
- Only one transition stage may be active at a time.
- A later stage must not compensate for an incomplete earlier stage.
- Existing production, Paper, Shadow and Research behavior must remain observable during migration.
- Real trading must not be enabled by this plan.
- Every stage follows: Inventory -> Analysis -> Contract -> Implementation -> Bash Test -> Review.
- Commit, tag, push, migration, service restart and destructive SQL require explicit operator approval.
- Every significant approved delivery is committed and pushed separately.
- Unrelated operator changes are never reverted or included.
- A stage is complete only after its exit gate and Bash verdict pass.

## 3. Stage 0 - Lock The Baseline

Goal: establish immutable architectural source documents and a reproducible baseline.

Required result:

- final architecture and Must Have documents are tracked by Git;
- contract test validates both documents;
- current services, routes, data freshness and Git state are inventoried;
- rollback point is identified;
- no runtime behavior changes.

Exit gate: `VERDICT=TEST_MARKETCORE_FINAL_ARCHITECTURE_AND_MUST_HAVE_V1_OK`.

## 4. Stage 1 - Presentation Inventory

Goal: measure the gap between the current presentation layer and the target architecture.

Inventory must identify:

- every RenderTree producer and consumer;
- HTML, DOM, CSS and browser semantics crossing domain boundaries;
- hardcoded user text and managed values;
- live, stale, snapshot and placeholder data sources;
- broken, simulated and working routes and actions;
- direct SQL or trading actions reachable from UI;
- missing message keys and fallback behavior;
- ownership of Runtime, Platform Driver and bootstrap components.

Required result: a versioned violation registry with owner, severity, evidence and target stage.

Exit gate: inventory Bash test proves complete coverage of the presentation surface.

## 5. Stage 2 - Domain RenderTree Contract

Goal: establish one platform-neutral UI domain contract.

The contract contains only domain node types, message keys, values, states, action identifiers and domain navigation targets.

The contract must not contain HTML tags, CSS classes, style properties, DOM events, browser-specific node types, SQL or trading logic.

Required result:

- one canonical `RenderDocument` and `RenderNode` model;
- serialization and validation contracts;
- compatibility strategy for existing producers;
- missing-key and forbidden-dependency tests.

Exit gate: all RenderTree contract and architecture boundary tests pass.

## 6. Stage 3 - Runtime And Platform Driver Boundary

Goal: enforce responsibility boundaries without changing business behavior.

Responsibilities:

- Presenter creates the domain RenderTree;
- Runtime validates documents and dispatches allowed domain actions;
- Platform Driver renders the document for a target platform;
- Browser DOM Driver is a platform implementation only;
- bootstrap shell only loads Runtime and contains no screen structure or business data.

Required result: no business logic in the DOM driver and no platform dependency in the domain Runtime.

Exit gate: driver contract, runtime dependency and bootstrap tests pass.

## 7. Stage 4 - Canonical Navigation Containers

Goal: restore the approved first-level information architecture.

The only first-level containers are:

1. Home;
2. Capital;
3. Edge;
4. Research;
5. Intraday;
6. Portfolio;
7. Risk;
8. Program;
9. Settings.

Each container must have a stable identifier, real domain target, loading state, empty state, failure state and localized label. Engineering and diagnostic pages must not appear in first-level navigation.

Exit gate: every container opens its real target through the Runtime action contract on desktop and mobile layouts.

## 8. Stage 5 - Policy-Governed Actions

Goal: make menu, card and object interactions operational.

Required result:

- click and double-click map to explicit domain action identifiers;
- navigation actions are separated from state-changing commands;
- every state-changing automatic action passes Policy Engine and Risk Engine where applicable;
- irreversible actions require separate operator confirmation;
- reversible actions define rollback;
- UI and AI never submit orders directly;
- all decisions and operator overrides enter the audit trail.

Exit gate: action contract, policy, authorization, duplicate-action and rollback tests pass.

## 9. Stage 6 - Complete I18n

Mandatory technical debt gate before live Runtime V2 cutover:

- audit every `content.message_key` emitted by every live RenderTree V2 producer;
- require a Russian translation for every emitted key and forbid rendering the technical key to the operator;
- verify every `message_args` substitution and Russian parameter label in every container;
- rerun this coverage gate after adding any producer, container, or action.

Goal: remove user-facing hardcode from the full presentation path.

Message dictionaries must cover menu items, headings, parameters, strategy names, statuses, verdicts, errors, actions, units and empty states.

Domain codes remain language-independent. Minimum locale is `ru-RU`; fallback and missing-key validation are mandatory.

Exit gate: zero missing keys and zero forbidden user-facing literals in presenters and renderers.

## 10. Stage 7 - Live Profit Funnel Data

Goal: replace stale or decorative aggregates with traceable live data.

The funnel is:

Research -> Candidate -> Validated Edge -> OOS -> Forward -> Shadow -> Paper -> Runtime -> Live -> Profit.

Every transition exposes count, conversion, latency, freshness, rejection reasons, net PnL, cost impact, risk impact and source identity where applicable.

Priority incidents addressed here include stale observations, stopped M5 bars, missing Paper replenishment and unchanged OOS/Shadow metrics.

Exit gate: freshness, lineage, reconciliation and data-quality tests pass for every displayed KPI.

## 11. Stage 8 - Operator Workspace

Goal: support evidence-based operational decisions.

Required result:

- bottleneck and loss source;
- ranked Top Actions;
- evidence and source freshness;
- expected Profit Impact and Risk Impact;
- confidence and sample sufficiency;
- policy verdict and autonomy mode;
- expiration and rollback plan;
- actual result and learning feedback.

Unverified data must never produce a green operational recommendation.

Exit gate: decision lineage from source evidence to result is reproducible and audited.

## 12. Stage 9 - Retire Legacy Presentation

Goal: remove compatibility paths only after all canonical containers work through the target path.

Required result:

- server-side screen generation is removed;
- HTML, CSS and DOM semantics are absent from the domain RenderTree and presenters;
- obsolete routes, adapters, placeholder actions and duplicate render paths are removed;
- minimal bootstrap and platform drivers remain;
- regression, responsive, i18n and architecture tests pass.

Exit gate: the legacy presentation path has zero callers and is removed with a documented rollback.

## 13. Critical Exception Protocol

Deviation is allowed only for a critical case:

- active risk of capital loss or unauthorized real execution;
- corrupted or irrecoverable source-of-truth data;
- security compromise;
- production outage blocking essential observation or control;
- architecture contract defect that makes compliant progress impossible.

Poor convenience, schedule pressure, cosmetic defects, desired refactoring and ordinary test failures are not critical cases.

Every critical exception requires:

1. incident identifier, evidence and severity;
2. explicit statement of the violated plan rule;
3. the smallest reversible intervention;
4. no expansion of trading permissions;
5. test and rollback plan before application when technically possible;
6. operator approval for restricted operations;
7. audit record and follow-up correction;
8. immediate return to the interrupted stage after stabilization.

An exception does not amend this plan. A permanent sequence change requires a new reviewed version of this document.

## 14. Stage Definition Of Done

A stage is complete only when:

- its objective is tied to Profit or Risk;
- sources and ownership are explicit;
- no managed hardcode is introduced;
- i18n and architecture boundaries are preserved;
- measurable acceptance criteria pass;
- Bash test prints an explicit successful `VERDICT`;
- real trading remains disabled;
- rollback is documented;
- review finds no unresolved critical issue;
- operator has explicitly approved any restricted delivery operation.

## 15. Current Position

Completed stages:

- Stage 0 - Lock The Baseline;
- Stage 1 - Presentation Inventory;
- Stage 2 - Domain RenderTree Contract;
- Stage 3 - Runtime And Platform Driver Boundary.

Current active stage: Stage 4 - Canonical Navigation Containers.

The mandatory Stage 6 i18n technical debt gate remains open and blocks live Runtime V2 cutover.

`VERDICT=MARKETCORE_STAGE3_RUNTIME_PLATFORM_COMPLETE`
