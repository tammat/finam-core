"use strict";

(function installMarketCoreBrowserPresentationServicesV2(globalObject) {
    const SERVICE_VERSION = "marketcore.browser_presentation_services.v2";
    const CATALOG_MEDIA_TYPE = "application/vnd.marketcore.i18n-catalog+json";

    class BrowserPresentationServicesErrorV2 extends Error {
        constructor(code, detail) {
            super(detail === undefined ? code : `${code}:${detail}`);
            this.name = "BrowserPresentationServicesErrorV2";
            this.code = code;
        }
    }

    function fail(code, detail) { throw new BrowserPresentationServicesErrorV2(code, detail); }

    function substitute(template, args) {
        return template.replace(/\{([A-Za-z0-9_]+)\}/g, (match, name) => {
            if (!Object.prototype.hasOwnProperty.call(args, name)) {
                fail("PRESENTATION_V2_MESSAGE_ARGUMENT_MISSING", name);
            }
            return String(args[name]);
        });
    }

    function createTranslator(catalog) {
        if (!catalog || catalog.schema_version !== "marketcore.i18n_catalog.v2") {
            fail("PRESENTATION_V2_CATALOG_INVALID");
        }
        const messages = catalog.messages || {};
        const missingMessages = new Set();
        const readableFallback = (messageKey) => {
            const raw = String(messageKey || "").split(".").pop().split(":").pop();
            const label = raw.replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();
            return label ? `Новый статус: ${label}` : "Новый статус";
        };
        return function translate(messageKey, messageArgs, localeCode) {
            const template = messages[messageKey];
            if (typeof template !== "string" || template === "") {
                if (!missingMessages.has(messageKey)) {
                    missingMessages.add(messageKey);
                    globalObject.console.error(
                        "PRESENTATION_V2_MESSAGE_MISSING",
                        `${localeCode}:${messageKey}`
                    );
                }
                return readableFallback(messageKey);
            }
            return substitute(template, messageArgs || {});
        };
    }

    function durationHm(value) {
        const totalSeconds = Math.max(0, Math.round(Number(value)));
        if (!Number.isFinite(totalSeconds)) fail("PRESENTATION_V2_DURATION_INVALID", String(value));
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        if (hours > 0 && minutes > 0) return `${hours} ч ${minutes} мин`;
        if (hours > 0) return `${hours} ч`;
        return `${minutes} мин`;
    }

    function domainValue(value, locale) {
        if (value === null || value === undefined || value === "") return "Нет данных";
        if (typeof value === "boolean") return value ? "Да" : "Нет";
        if (Array.isArray(value)) {
            return value.length
                ? value.map((item) => domainValue(item, locale)).join(", ")
                : "Нет данных";
        }
        if (typeof value === "object") {
            const entries = Object.entries(value);
            if (!entries.length) return "Нет параметров";
            return entries
                .map(([key, item]) => `${key.replace(/_/g, " ")}: ${domainValue(item, locale)}`)
                .join(" · ");
        }
        return String(value);
    }

    function createFormatter() {
        return function format(value, formatCode, localeCode, timezoneCode) {
            const locale = localeCode || "ru-RU";
            switch (formatCode) {
                case "DATETIME":
                    return new Intl.DateTimeFormat(locale, {
                        timeZone: timezoneCode, dateStyle: "short", timeStyle: "medium"
                    }).format(new Date(value));
                case "DURATION_HM": return durationHm(value);
                case "INTEGER": return new Intl.NumberFormat(locale, {maximumFractionDigits: 0}).format(Number(value));
                case "DECIMAL": return new Intl.NumberFormat(locale, {maximumFractionDigits: 4}).format(Number(value));
                case "MONEY_RUB": return new Intl.NumberFormat(locale, {style: "currency", currency: "RUB"}).format(Number(value));
                case "PERCENT": return `${new Intl.NumberFormat(locale, {maximumFractionDigits: 2}).format(Number(value))}%`;
                case "PERCENT_RATIO": return new Intl.NumberFormat(locale, {style: "percent", maximumFractionDigits: 2}).format(Number(value));
                case "BOOLEAN": return domainValue(Boolean(value), locale);
                case "DOMAIN_VALUE": return domainValue(value, locale);
                case "DOMAIN_CODE": return String(value || "").replace(/[_-]+/g, " ");
                case null:
                case undefined: return domainValue(value, locale);
                default: return domainValue(value, locale);
            }
        };
    }

    async function load(options) {
        const localeCode = options && options.localeCode ? options.localeCode : "ru-RU";
        if (typeof globalObject.fetch !== "function") fail("PRESENTATION_V2_FETCH_REQUIRED");
        const endpoint = `/api/v2/i18n/catalog?locale=${encodeURIComponent(localeCode)}`;
        const response = await globalObject.fetch(endpoint, {
            method: "GET", headers: {Accept: CATALOG_MEDIA_TYPE}, credentials: "same-origin", cache: "no-store"
        });
        if (!response.ok) fail("PRESENTATION_V2_CATALOG_HTTP_FAILED", String(response.status));
        const contentType = response.headers.get("content-type") || "";
        if (!contentType.toLowerCase().startsWith(CATALOG_MEDIA_TYPE)) {
            fail("PRESENTATION_V2_CATALOG_CONTENT_TYPE_INVALID", contentType);
        }
        const catalog = await response.json();
        return Object.freeze({localeCode, translate: createTranslator(catalog), format: createFormatter()});
    }

    globalObject.MarketCoreBrowserPresentationServicesV2 = Object.freeze({
        serviceVersion: SERVICE_VERSION,
        ServiceError: BrowserPresentationServicesErrorV2,
        createTranslator,
        createFormatter,
        load
    });
})(globalThis);
