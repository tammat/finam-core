"use strict";

(function installMarketCoreRenderTreeValidatorV2(globalObject) {
    const SCHEMA_VERSION = "marketcore.render_tree.v2";
    const MAXIMUM_DEPTH = 32;
    const MAXIMUM_NODES = 10000;
    const NODE_TYPES = new Set([
        "workspace", "page", "header", "section", "grid", "card",
        "table", "table_head", "table_body", "table_row",
        "table_header_cell", "table_cell", "title", "subtitle", "text",
        "metric_list", "metric_row", "metric_label", "metric_value",
        "action", "badge"
    ]);
    const ACTION_KINDS = new Set(["NAVIGATE", "QUERY", "COMMAND", "CONFIRM"]);

    class RenderTreeValidationErrorV2 extends Error {
        constructor(code, detail) {
            super(detail === undefined ? code : `${code}:${detail}`);
            this.name = "RenderTreeValidationErrorV2";
            this.code = code;
            this.detail = detail;
        }
    }

    function fail(code, detail) {
        throw new RenderTreeValidationErrorV2(code, detail);
    }

    function requireObject(value, code) {
        if (value === null || typeof value !== "object" || Array.isArray(value)) fail(code);
    }

    function requireCode(value, code) {
        if (typeof value !== "string" || value.trim() === "") fail(code);
    }

    function validate(payload) {
        requireObject(payload, "RENDER_TREE_V2_DOCUMENT_REQUIRED");
        if (payload.schema_version !== SCHEMA_VERSION) {
            fail("RENDER_TREE_V2_SCHEMA_VERSION_UNSUPPORTED", payload.schema_version);
        }
        for (const field of ["document_id", "locale_code", "fallback_locale_code", "timezone_code", "generated_at", "source_as_of", "quality_code"]) {
            requireCode(payload[field], `RENDER_TREE_V2_${field.toUpperCase()}_INVALID`);
        }
        requireObject(payload.root, "RENDER_TREE_V2_ROOT_REQUIRED");
        if (payload.root.type !== "workspace") fail("RENDER_TREE_V2_ROOT_TYPE_INVALID");

        const identifiers = new Set();
        let nodeCount = 0;
        function visit(node, depth) {
            requireObject(node, "RENDER_TREE_V2_NODE_REQUIRED");
            if (depth > MAXIMUM_DEPTH) fail("RENDER_TREE_V2_MAXIMUM_DEPTH_EXCEEDED");
            if (!NODE_TYPES.has(node.type)) fail("RENDER_TREE_V2_NODE_TYPE_UNSUPPORTED", node.type);
            requireCode(node.node_id, "RENDER_TREE_V2_NODE_ID_INVALID");
            if (identifiers.has(node.node_id)) fail("RENDER_TREE_V2_NODE_ID_DUPLICATE", node.node_id);
            identifiers.add(node.node_id);
            nodeCount += 1;
            if (nodeCount > MAXIMUM_NODES) fail("RENDER_TREE_V2_MAXIMUM_NODES_EXCEEDED");
            if (!Array.isArray(node.children)) fail("RENDER_TREE_V2_CHILDREN_REQUIRED", node.node_id);
            if (node.content !== undefined) {
                requireObject(node.content, "RENDER_TREE_V2_CONTENT_INVALID");
                if (node.content.message_key === undefined && node.content.value === undefined) {
                    fail("RENDER_TREE_V2_CONTENT_EMPTY", node.node_id);
                }
                if (node.content.message_key !== undefined) {
                    requireCode(node.content.message_key, "RENDER_TREE_V2_MESSAGE_KEY_INVALID");
                }
            }
            if (node.action !== undefined) {
                requireObject(node.action, "RENDER_TREE_V2_ACTION_INVALID");
                requireCode(node.action.action_id, "RENDER_TREE_V2_ACTION_ID_INVALID");
                if (!ACTION_KINDS.has(node.action.action_kind)) {
                    fail("RENDER_TREE_V2_ACTION_KIND_INVALID", node.action.action_kind);
                }
            }
            node.children.forEach(child => visit(child, depth + 1));
        }
        visit(payload.root, 1);
        return Object.freeze({schemaVersion: SCHEMA_VERSION, nodeCount});
    }

    globalObject.MarketCoreRenderTreeValidatorV2 = Object.freeze({
        schemaVersion: SCHEMA_VERSION,
        ValidationError: RenderTreeValidationErrorV2,
        validate
    });
})(globalThis);
