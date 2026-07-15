# MARKETCORE PRESENTATION INVENTORY V1

Version: 1.0
Status: BASELINE
Captured: 2026-07-15
Target plan stage: Stage 1 - Presentation Inventory

## 1. Scope

Static scope: `src/marketcore/presentation` at commit `3107a73e`.

Runtime probe: `http://127.0.0.1:8080` on the project server.

This registry records evidence. It does not authorize runtime, database, migration or service changes.

## 2. Surface Baseline

| Metric | Baseline |
|---|---:|
| Presentation files excluding `__pycache__` | 287 |
| Python files | 258 |
| JavaScript files | 8 |
| CSS files | 2 |
| RenderTree files | 6 |
| UI Runtime files | 14 |
| Page files | 64 |
| Workspace V2 files | 48 |
| Dashboard files | 25 |
| RenderNode references | 252 |
| RenderDocument references | 29 |
| RenderNode `class` props | 44 |
| RenderNode `style` props | 14 |
| HTMLResponse references | 33 |
| SQL statement references in Presentation | 196 |

Counts are discovery indicators, not deletion targets. A reference is removed only after ownership and behavior are understood.

## 3. Presentation Paths

| Path | Current responsibility | Target owner | Target stage |
|---|---|---|---:|
| `presentation/render_tree` | Domain nodes, serialization, HTTP response helper | Domain RenderTree | 2 |
| `presentation/ui_runtime/contract_v1.py` | Runtime payload rules | Domain Runtime | 2 |
| `presentation/ui_runtime/assets/v1` | Browser executor, DOM driver, bootstrap and CSS | Platform Driver | 3 and 9 |
| `presentation/adapters/web` | RenderDocument-to-HTML adapter | Legacy compatibility | 9 |
| `presentation/dashboard` | Independent HTML dashboard routers/renderers | Dashboard 8088 or legacy | 1 and 9 |
| `presentation/pages` | Mixed page construction and HTML responses | Presenter | 2 through 7 |
| `presentation/workspace_v2` | Mixed resolver, presenter, HTML, CSS, SQL and actions | Split by contract | 2 through 8 |
| `presentation/providers` | Data access and UI models | Application query services | 6 and 7 |
| `presentation/i18n` | Partial localization | I18n | 6 |

## 4. Runtime Route Probe

| Route | HTTP | Observed content type | Finding |
|---|---:|---|---|
| `/` | 200 | `text/html` | Minimal runtime shell present |
| `/workspace-v2` | 200 | `text/html` | Same runtime shell present |
| `/validation` | 404 | `text/html` | Canonical destination unavailable |
| `/edge-factory` | 404 | `text/html` | Canonical destination unavailable |
| `/edge-score-shadow` | 404 | `text/html` | Canonical destination unavailable |
| `/system` | 404 | `text/html` | Canonical destination unavailable |
| `/risk` | 404 | `text/html` | Canonical destination unavailable |
| `/research` | 404 | `text/html` | Canonical destination unavailable |
| `/feature-store` | 404 | `text/html` | Canonical destination unavailable |
| `/api/v2/render-tree/control-center/edge` | 200 | reported as `text/html` by route metadata | Body is RenderTree JSON; response metadata requires correction |

Runtime results are time-bound evidence and must be re-probed before implementation.

## 5. Violation Registry

| ID | Severity | Evidence | Owner | Target stage | Acceptance condition |
|---|---|---|---|---:|---|
| PRES-001 | Critical | `UiRuntimeContractV1` permits `class` and `style` in domain node props | RenderTree contract | 2 | Domain contract rejects CSS semantics |
| PRES-002 | Critical | Browser driver maps domain `class` and `style` directly to DOM attributes | Platform Driver | 2 and 3 | Domain payload contains no CSS semantics |
| PRES-003 | High | `RenderNode.node_type` accepts arbitrary strings for temporary compatibility | RenderTree contract | 2 | Only registered domain node types pass validation |
| PRES-004 | High | `render_document_to_html_v1.py` and multiple HTML render paths remain active in source | Legacy presentation | 9 | Zero callers before adapter removal |
| PRES-005 | Critical | Workspace V2 combines HTML, CSS, forms, queries and operator actions | Presentation/Application split | 2, 3, 5 and 7 | Each responsibility crosses only an approved contract |
| PRES-006 | Critical | 196 SQL statement references exist under Presentation; top sources include control-center resolver and legacy workspace | Application query services | 7 | UI presenters use approved APIs/query services and no direct PostgreSQL access |
| PRES-007 | High | User-facing Russian text exists in presenters, labels, pages and JavaScript dialogs | I18n | 6 | Message keys, `ru-RU` fallback and missing-key test cover all user text |
| PRES-008 | High | DOM driver contains confirmation labels and behavior-specific navigation logic | Runtime/Platform Driver | 3, 5 and 6 | Driver renders and emits domain actions without business decisions or hardcoded labels |
| PRES-009 | Critical | Seven existing canonical analysis routes return 404 on port 8080 | Navigation | 4 | All nine canonical containers open real Runtime targets |
| PRES-010 | High | Home and Control Center cards target engineering `/workspace-v2/control-center/edge-oos/*` routes | Information architecture | 4 | First-level cards target approved domain containers |
| PRES-011 | High | RenderTree API body is JSON while observed route metadata reports `text/html` | Runtime HTTP adapter | 3 | JSON endpoint reports the approved JSON media type |
| PRES-012 | Critical | Browser actions navigate or display progress without a Policy Engine decision contract | Action Runtime | 5 | State-changing actions require policy verdict, audit and rollback metadata |
| PRES-013 | High | Browser driver contains simulated 15% -> 100% progress independent of server action state | Action Runtime | 5 | Progress derives from audited action status |
| PRES-014 | Critical | Current architecture has no proven end-to-end freshness lineage for all displayed OOS, Forward, Shadow and Paper KPIs | Data/API | 7 | Every KPI exposes source identity, as-of time and quality verdict |
| PRES-015 | High | Dashboard, legacy pages and Workspace V2 coexist with overlapping routes and rendering models | Presentation ownership | 1 and 9 | Each route has one documented owner; legacy callers reach zero before retirement |
| PRES-016 | Medium | `control_center_runtime_v2.html` and `home_runtime_v1.html` require review against minimal bootstrap constraints | Bootstrap | 3 | Shell contains no screen structure or business data |

## 6. Hardcode Hotspots

Priority files by Russian-token evidence:

1. `workspace_v2/edge_oos_control_center_v1.py`;
2. `ui_labels.py`;
3. `ui_text.py`;
4. `workspace_v2/presenter/control_center_v2_presenter.py`;
5. `pages/paper_edge_discovery.py`;
6. `pages/home.py`;
7. `workspace_v2/portfolio_v1.py`;
8. `ui_runtime/assets/v1/portfolio_workspace_v1.js`;
9. `ui_runtime/assets/v1/browser_dom_driver_v1.js`.

Russian source text is not automatically a violation. User-facing literals outside message dictionaries are violations; comments, domain documentation and localized dictionary values are allowed.

## 7. SQL Hotspots

Priority files by SQL-token evidence:

1. `workspace_v2/resolver/control_center_v2_resolver.py`;
2. `workspace_v2/edge_oos_control_center_v1.py`;
3. `workspace_v2/presenter/home_v2_presenter.py`;
4. `pages/ai_registry.py`;
5. `providers/discovery_control_provider.py`;
6. `pages/serve_knowledge_graph_view_v1.py`;
7. `workspace_v2/portfolio_v1.py`.

Stage 7 must distinguish direct database access from approved application query services before moving code.

## 8. Risk Controls

- No legacy path is deleted during inventory.
- No route is redirected during inventory.
- No SQL, migration, timer or service is executed by inventory tests.
- No Paper, Shadow, Runtime or Live permission changes are allowed.
- Current operator and MX proxy worktree changes remain outside this inventory delivery.

## 9. Stage 1 Exit Gate

Stage 1 is complete when:

- all presentation subtrees have an owner and target stage;
- HTML/DOM/CSS, hardcode, SQL, route, action and data-freshness categories are represented;
- every registered violation has severity, evidence, owner, target stage and acceptance condition;
- the inventory Bash test passes;
- review finds no unclassified critical presentation category.

`VERDICT=MARKETCORE_PRESENTATION_INVENTORY_V1_COMPLETE`
