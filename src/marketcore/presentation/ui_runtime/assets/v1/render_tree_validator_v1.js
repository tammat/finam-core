"use strict";

(function installMarketCoreRenderTreeValidatorV1(globalObject) {
    const SCHEMA_VERSION = "marketcore.render_tree.v1";
    const MAX_TREE_DEPTH = 32;
    const MAX_NODE_COUNT = 10000;

    const NODE_RULES = Object.freeze({
        workspace: {
            allowedProps: [
                "class",
                "style",
                "role",
                "aria_label",
                "data-section",
                "data-card",
                "data-status",
                "data-field"
            ],
            requiredProps: [],
            allowsText: false,
            allowsChildren: true
        },
        page: {
            allowedProps: [
                "class",
                "style",
                "role",
                "aria_label",
                "data-section",
                "data-card",
                "data-status",
                "data-field"
            ],
            requiredProps: [],
            allowsText: false,
            allowsChildren: true
        },
        header: {
            allowedProps: [
                "class",
                "style",
                "role",
                "aria_label",
                "data-field"
            ],
            requiredProps: [],
            allowsText: true,
            allowsChildren: true
        },
        section: {
            allowedProps: [
                "class",
                "style",
                "role",
                "aria_label",
                "data-section",
                "data-card",
                "data-status",
                "data-field"
            ],
            requiredProps: [],
            allowsText: false,
            allowsChildren: true
        },
        grid: {
            allowedProps: [
                "class",
                "style",
                "role",
                "aria_label",
                "data-section",
                "data-card",
                "data-status",
                "data-field"
            ],
            requiredProps: [],
            allowsText: false,
            allowsChildren: true
        },
        card: {
            allowedProps: [
                "class",
                "style",
                "role",
                "aria_label",
                "data-section",
                "data-card",
                "data-status",
                "data-availability",
                "data-field"
            ],
            requiredProps: [],
            allowsText: false,
            allowsChildren: true
        },
        title: {
            allowedProps: [
                "class",
                "style",
                "role",
                "aria_label",
                "data-field",
                "level"
            ],
            requiredProps: ["level"],
            allowsText: true,
            allowsChildren: false
        },
        subtitle: {
            allowedProps: [
                "class",
                "style",
                "role",
                "aria_label",
                "data-field"
            ],
            requiredProps: [],
            allowsText: true,
            allowsChildren: false
        },
        text: {
            allowedProps: [
                "class",
                "style",
                "role",
                "aria_label",
                "data-availability",
                "data-field"
            ],
            requiredProps: [],
            allowsText: true,
            allowsChildren: false
        },
        metric_list: {
            allowedProps: [
                "class",
                "style",
                "role",
                "aria_label",
                "data-section",
                "data-card",
                "data-status",
                "data-field"
            ],
            requiredProps: [],
            allowsText: false,
            allowsChildren: true
        },
        metric_row: {
            allowedProps: [
                "class",
                "style",
                "role",
                "aria_label",
                "data-section",
                "data-card",
                "data-status",
                "data-field"
            ],
            requiredProps: [],
            allowsText: false,
            allowsChildren: true
        },
        metric_label: {
            allowedProps: [
                "class",
                "style",
                "role",
                "aria_label",
                "data-field"
            ],
            requiredProps: [],
            allowsText: true,
            allowsChildren: false
        },
        metric_value: {
            allowedProps: [
                "class",
                "style",
                "role",
                "aria_label",
                "data-field"
            ],
            requiredProps: [],
            allowsText: true,
            allowsChildren: false
        },
        action: {
            allowedProps: [
                "class",
                "style",
                "role",
                "aria_label",
                "href",
                "action_code",
                "target",
                "disabled"
            ],
            requiredProps: [],
            allowsText: true,
            allowsChildren: false
        },
        badge: {
            allowedProps: [
                "class",
                "style",
                "role",
                "aria_label",
                "data-field",
                "status"
            ],
            requiredProps: [],
            allowsText: true,
            allowsChildren: false
        }
    });

    class RenderTreeValidationErrorV1 extends Error {
        constructor(code, detail) {
            super(detail === undefined ? code : `${code}:${detail}`);
            this.name = "RenderTreeValidationErrorV1";
            this.code = code;
            this.detail = detail;
        }
    }

    function isPlainObject(value) {
        return (
            value !== null
            && typeof value === "object"
            && !Array.isArray(value)
        );
    }

    function fail(code, detail) {
        throw new RenderTreeValidationErrorV1(code, detail);
    }

    function validateActionTarget(props) {
        const target = props.target !== undefined
            ? props.target
            : props.href;

        if (target === undefined || target === null) {
            return;
        }

        if (typeof target !== "string") {
            fail("RENDER_TREE_ACTION_TARGET_MUST_BE_STRING");
        }

        if (
            !target.startsWith("/")
            && !target.startsWith("http://")
            && !target.startsWith("https://")
        ) {
            fail(
                "RENDER_TREE_ACTION_TARGET_SCHEME_FORBIDDEN",
                target
            );
        }
    }

    function validateNode(node, state, depth) {
        if (!isPlainObject(node)) {
            fail("RENDER_TREE_NODE_MUST_BE_OBJECT");
        }

        if (depth > MAX_TREE_DEPTH) {
            fail("RENDER_TREE_MAXIMUM_DEPTH_EXCEEDED");
        }

        state.nodeCount += 1;

        if (state.nodeCount > MAX_NODE_COUNT) {
            fail("RENDER_TREE_MAXIMUM_NODE_COUNT_EXCEEDED");
        }

        const nodeType = node.type;

        if (typeof nodeType !== "string") {
            fail("RENDER_TREE_NODE_TYPE_MUST_BE_STRING");
        }

        const rule = NODE_RULES[nodeType];

        if (rule === undefined) {
            fail("RENDER_TREE_NODE_TYPE_UNSUPPORTED", nodeType);
        }

        const props = node.props === undefined ? {} : node.props;

        if (!isPlainObject(props)) {
            fail(
                "RENDER_TREE_NODE_PROPS_MUST_BE_OBJECT",
                nodeType
            );
        }

        const allowedProps = new Set(rule.allowedProps);

        for (const propName of Object.keys(props)) {
            if (!allowedProps.has(propName)) {
                fail(
                    "RENDER_TREE_NODE_PROP_UNSUPPORTED",
                    `${nodeType}:${propName}`
                );
            }
        }

        for (const requiredProp of rule.requiredProps) {
            if (!Object.prototype.hasOwnProperty.call(
                props,
                requiredProp
            )) {
                fail(
                    "RENDER_TREE_NODE_PROP_REQUIRED",
                    `${nodeType}:${requiredProp}`
                );
            }
        }

        const text = node.text === undefined ? "" : node.text;

        if (typeof text !== "string") {
            fail(
                "RENDER_TREE_NODE_TEXT_MUST_BE_STRING",
                nodeType
            );
        }

        if (text !== "" && !rule.allowsText) {
            fail(
                "RENDER_TREE_NODE_TEXT_NOT_ALLOWED",
                nodeType
            );
        }

        const children = node.children === undefined
            ? []
            : node.children;

        if (!Array.isArray(children)) {
            fail(
                "RENDER_TREE_NODE_CHILDREN_MUST_BE_ARRAY",
                nodeType
            );
        }

        if (children.length > 0 && !rule.allowsChildren) {
            fail(
                "RENDER_TREE_NODE_CHILDREN_NOT_ALLOWED",
                nodeType
            );
        }

        if (
            nodeType === "title"
            && ![1, 2, 3].includes(props.level)
        ) {
            fail(
                "RENDER_TREE_TITLE_LEVEL_INVALID",
                String(props.level)
            );
        }

        if (nodeType === "action") {
            validateActionTarget(props);
        }

        for (const child of children) {
            validateNode(child, state, depth + 1);
        }
    }

    function validate(payload) {
        if (!isPlainObject(payload)) {
            fail("RENDER_TREE_PAYLOAD_MUST_BE_OBJECT");
        }

        if (payload.schema_version !== SCHEMA_VERSION) {
            fail(
                "RENDER_TREE_SCHEMA_VERSION_UNSUPPORTED",
                String(payload.schema_version)
            );
        }

        if (!isPlainObject(payload.root)) {
            fail("RENDER_TREE_ROOT_MUST_BE_OBJECT");
        }

        if (payload.root.type !== "workspace") {
            fail(
                "RENDER_TREE_ROOT_TYPE_INVALID",
                String(payload.root.type)
            );
        }

        const state = {
            nodeCount: 0
        };

        validateNode(payload.root, state, 1);

        return Object.freeze({
            valid: true,
            schemaVersion: payload.schema_version,
            nodeCount: state.nodeCount
        });
    }

    globalObject.MarketCoreRenderTreeValidatorV1 = Object.freeze({
        schemaVersion: SCHEMA_VERSION,
        maximumTreeDepth: MAX_TREE_DEPTH,
        maximumNodeCount: MAX_NODE_COUNT,
        supportedNodeTypes: Object.freeze(
            Object.keys(NODE_RULES)
        ),
        ValidationError: RenderTreeValidationErrorV1,
        validate
    });
})(globalThis);
