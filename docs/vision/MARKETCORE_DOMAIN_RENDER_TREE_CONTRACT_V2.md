# MARKETCORE DOMAIN RENDER TREE CONTRACT V2

Version: 2.0
Status: LOCKED TARGET CONTRACT
Schema: `marketcore.render_tree.v2`
Plan stage: Stage 2 - Domain RenderTree Contract

## 1. Purpose

RenderTree is the platform-neutral domain description of an operator workspace. It communicates meaning, values, state and permitted interactions. It does not describe browser markup or visual styling.

V2 is the only target contract for new and migrated producers. V1 exists only as a temporary compatibility input until its registered callers reach zero in Stage 9.

## 2. Ownership

- Presenter produces a V2 `RenderDocument`.
- Domain Runtime validates the document and action declarations.
- Platform Driver renders validated nodes for its target platform.
- I18n resolves message keys for the selected locale.
- Policy and Risk engines authorize state-changing actions.

## 3. Document Envelope

Required fields:

- `schema_version`: exactly `marketcore.render_tree.v2`;
- `document_id`: stable non-empty identifier;
- `locale_code`: requested locale code;
- `fallback_locale_code`: required fallback locale;
- `generated_at`: UTC timestamp;
- `source_as_of`: UTC timestamp of the least-fresh source represented;
- `quality_code`: domain data-quality verdict;
- `root`: one `workspace` node.

Unknown envelope fields are rejected.

## 4. Node Envelope

Each node contains only:

- `type`: registered domain node type;
- `node_id`: stable identifier within the document;
- `content`: optional domain content object;
- `state`: optional domain state object;
- `action`: optional action declaration;
- `children`: ordered child nodes.

Unknown node fields are rejected. Arbitrary string node types are rejected.

## 5. Domain Node Types

The V2 registry contains:

- `workspace`;
- `page`;
- `header`;
- `section`;
- `grid`;
- `card`;
- `table`;
- `table_head`;
- `table_body`;
- `table_row`;
- `table_header_cell`;
- `table_cell`;
- `title`;
- `subtitle`;
- `text`;
- `metric_list`;
- `metric_row`;
- `metric_label`;
- `metric_value`;
- `action`;
- `badge`.

Platform node types such as `html`, `body`, `main`, `div`, `article`, `h1`, `a`, `dialog`, `form`, `button` and `select` are forbidden.

## 6. Content Contract

Allowed content fields:

- `message_key`: localization key for user-facing text;
- `message_args`: structured interpolation values;
- `value`: domain value, never preformatted HTML;
- `format_code`: registered number, money, percent, timestamp or domain-code formatter;
- `level_code`: domain title level where applicable;
- `column_code`: stable table column identifier.

Rules:

- user-facing literals are forbidden;
- `message_key` and `value` have distinct meanings;
- domain codes are not translated in storage;
- message arguments are data, not markup;
- HTML entities and markup fragments are forbidden.

## 7. State Contract

Allowed state fields:

- `status_code`;
- `quality_code`;
- `availability_code`;
- `freshness_code`;
- `selected`;
- `disabled_reason_code`;
- `source_as_of`;
- `source_identity`.

Status and quality are domain codes. Colors and CSS names are forbidden. A Platform Driver decides how a code is represented.

## 8. Action Contract

Allowed action fields:

- `action_id`;
- `action_kind`: `NAVIGATE`, `QUERY`, `COMMAND` or `CONFIRM`;
- `target_id`;
- `command_code`;
- `policy_class`;
- `requires_approval`;
- `reversible`;
- `rollback_code`;
- `expiration`;
- `idempotency_key`;
- `enabled`;
- `blocked_reason_code`.

Rules:

- `href`, URL schemes and HTTP methods are platform adapter concerns;
- DOM event names are forbidden;
- UI and AI never declare direct broker or order actions;
- state-changing commands require Policy Engine metadata;
- irreversible commands require operator approval;
- enabled state does not bypass Policy or Risk.

## 9. Forbidden Semantics

RenderTree V2 must reject:

- `class`, `class_name` and CSS selectors;
- `style`, dimensions, pixels and layout declarations;
- HTML tags, attributes, entities and fragments;
- DOM roles, event names and `data-*` attributes;
- browser URLs, history and navigation APIs;
- JavaScript, executable callbacks and code strings;
- SQL and database connection details;
- trading, broker, order and fill execution logic;
- hardcoded display text;
- environment-specific values.

## 10. Validation

Validation is fail-closed and runs before a document reaches a Platform Driver.

It verifies:

- exact schema version;
- envelope shape;
- registered node types;
- allowed fields by node type;
- unique node identifiers;
- maximum depth and node count;
- message-key presence and fallback availability;
- UTC timestamps and source freshness metadata;
- action completeness and policy metadata;
- absence of forbidden platform semantics.

Validation errors use stable machine-readable codes and contain no platform instructions.

## 11. Serialization

Serialization is deterministic:

- identical input produces identical output;
- object keys are stable;
- children preserve domain order;
- no executable object is serialized;
- no platform-specific default is injected;
- timestamps use UTC ISO 8601.

## 12. Compatibility Boundary

V1 producers are migration inputs only. Compatibility rules are isolated outside the V2 domain model.

The compatibility boundary:

- may read a registered V1 payload;
- must reject unknown V1 fields;
- removes no security or policy restriction;
- records producer identity and conversion warnings;
- cannot introduce HTML, CSS, DOM or display literals into V2;
- cannot be used by new producers;
- is deleted in Stage 9 after zero-caller evidence.

V2 validators and models must not import V1 compatibility adapters.

## 13. Migration Order

1. Implement V2 immutable models and validator.
2. Implement deterministic serialization.
3. Add forbidden-semantics and missing-key tests.
4. Migrate Home producer.
5. Migrate canonical container producers.
6. Migrate Control Center and Portfolio producers.
7. Switch Runtime to validated V2 documents.
8. Move platform representation into Platform Driver.
9. Measure V1 callers until zero.
10. Retire V1 compatibility in Stage 9.

## 14. Definition Of Done

Stage 2 is complete only when:

- V2 models, validator and serializer exist;
- all active canonical producers emit valid V2;
- RenderTree contains zero HTML, CSS, DOM and browser semantics;
- all user-facing content uses message keys;
- all actions use the domain action contract;
- V2 has no dependency on V1 adapters or Platform Drivers;
- Bash contract and regression tests pass;
- runtime trading permissions remain unchanged.

`VERDICT=MARKETCORE_DOMAIN_RENDER_TREE_CONTRACT_V2_LOCKED`
