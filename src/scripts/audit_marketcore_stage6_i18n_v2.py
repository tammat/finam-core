from __future__ import annotations

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass

import psycopg2

from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import (
    DomainProducerCodeV2,
    build_domain_document_v2,
)


PLACEHOLDER = re.compile(r"\{([A-Za-z0-9_]+)\}")
CYRILLIC = re.compile(r"[А-Яа-яЁё]")
SEMANTIC_TEXT_TYPES = frozenset({"title", "subtitle", "metric_label", "table_header_cell", "action"})
STATE_PREFIX = {
    "status_code": "status",
    "quality_code": "quality",
    "availability_code": "availability",
    "freshness_code": "freshness",
}
FORBIDDEN_OPERATOR_TERMS = {
    "edge": re.compile(r"(?i)(?<![A-Za-z])edge(?![A-Za-z])"),
    "oos": re.compile(r"(?i)(?<![A-Za-z])oos(?![A-Za-z])"),
    "pnl": re.compile(r"(?i)(?<![A-Za-z])p\s*&?\s*l(?![A-Za-z])"),
    "roi": re.compile(r"(?i)(?<![A-Za-z])roi(?![A-Za-z])"),
    "paper": re.compile(r"(?i)(?<![A-Za-z])paper(?![A-Za-z])"),
    "shadow": re.compile(r"(?i)(?<![A-Za-z])shadow(?![A-Za-z])"),
    "forward": re.compile(r"(?i)(?<![A-Za-z])forward(?![A-Za-z])"),
    "live": re.compile(r"(?i)(?<![A-Za-z])live(?![A-Za-z])"),
    "bid/ask": re.compile(r"(?i)(?<![A-Za-z])bid\s*/\s*ask(?![A-Za-z])"),
    "atr": re.compile(r"(?i)(?<![A-Za-z])atr(?![A-Za-z])"),
}


@dataclass(frozen=True, slots=True)
class MessageOccurrence:
    producer: str
    node_id: str
    message_key: str
    message_args: frozenset[str]


def _walk(node, producer: str, messages, state_keys, hardcodes, domain_text) -> None:
    content = node.content
    if content is not None:
        if content.message_key:
            messages.append(MessageOccurrence(
                producer, node.node_id, content.message_key,
                frozenset((content.message_args or {}).keys()),
            ))
        elif isinstance(content.value, str) and content.value:
            if node.node_type.value in SEMANTIC_TEXT_TYPES:
                hardcodes.append((producer, node.node_id, node.node_type.value, content.value))
            elif CYRILLIC.search(content.value):
                domain_text.append((producer, node.node_id, content.value))
    if node.state is not None:
        for field, prefix in STATE_PREFIX.items():
            code = getattr(node.state, field)
            if code:
                state_keys.add(f"{prefix}.{str(code).lower()}")
    for child in node.children:
        _walk(child, producer, messages, state_keys, hardcodes, domain_text)


def _catalog() -> dict[str, str]:
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT resource_key,caption FROM presentation.ui_resource_v1 WHERE locale_code=%s",
                ("ru",),
            )
            return {str(key): str(caption or "") for key, caption in cursor.fetchall()}


def audit() -> dict[str, object]:
    catalog = _catalog()
    messages: list[MessageOccurrence] = []
    state_keys: set[str] = set()
    hardcodes: list[tuple[str, str, str, str]] = []
    domain_text: list[tuple[str, str, str]] = []
    producer_counts: dict[str, int] = {}
    for producer in DomainProducerCodeV2:
        document = build_domain_document_v2(producer)
        before = len(messages)
        state_keys.add(f"quality.{document.quality_code.lower()}")
        _walk(document.root, producer.value, messages, state_keys, hardcodes, domain_text)
        producer_counts[producer.value] = len(messages) - before

    emitted_keys = {item.message_key for item in messages}
    missing_messages = sorted(emitted_keys - catalog.keys())
    missing_states = sorted(state_keys - catalog.keys())
    blank = sorted(key for key in emitted_keys & catalog.keys() if not catalog[key].strip())
    technical_echo = sorted(key for key in emitted_keys & catalog.keys() if catalog[key].strip() == key)
    terminology_errors = sorted(
        f"{key}:{term}:{catalog[key]}"
        for key in emitted_keys & catalog.keys()
        for term, pattern in FORBIDDEN_OPERATOR_TERMS.items()
        if pattern.search(catalog[key])
    )
    argument_errors: list[str] = []
    for item in messages:
        caption = catalog.get(item.message_key)
        if caption is None:
            continue
        expected = frozenset(PLACEHOLDER.findall(caption))
        if expected != item.message_args:
            argument_errors.append(
                f"{item.producer}:{item.node_id}:{item.message_key}:"
                f"expected={sorted(expected)}:actual={sorted(item.message_args)}"
            )
    by_producer: dict[str, set[str]] = defaultdict(set)
    for item in messages:
        if item.message_key in missing_messages:
            by_producer[item.producer].add(item.message_key)
    return {
        "producer_counts": producer_counts,
        "message_occurrences": len(messages),
        "unique_message_keys": len(emitted_keys),
        "catalog_entries_ru": len(catalog),
        "missing_messages": missing_messages,
        "missing_states": missing_states,
        "blank_captions": blank,
        "technical_echo": technical_echo,
        "terminology_errors": terminology_errors,
        "argument_errors": sorted(set(argument_errors)),
        "semantic_hardcodes": hardcodes,
        "domain_text_values": domain_text,
        "missing_by_producer": {key: sorted(value) for key, value in sorted(by_producer.items())},
    }


def _print_report(result: dict[str, object]) -> None:
    print("# MarketCore Stage 6 I18n Audit V2")
    print()
    print(f"message_occurrences={result['message_occurrences']}")
    print(f"unique_message_keys={result['unique_message_keys']}")
    print(f"catalog_entries_ru={result['catalog_entries_ru']}")
    for name in ("missing_messages", "missing_states", "blank_captions", "technical_echo", "terminology_errors", "argument_errors", "semantic_hardcodes"):
        print(f"{name}={len(result[name])}")
    print(f"domain_text_values={len(result['domain_text_values'])}")
    print()
    print("## Producers")
    for producer, count in result["producer_counts"].items():
        missing = len(result["missing_by_producer"].get(producer, ()))
        print(f"- {producer}: occurrences={count}, missing_unique={missing}")
    for heading, field in (
        ("Missing Russian Message Keys", "missing_messages"),
        ("Missing State Translations", "missing_states"),
        ("Forbidden Operator Terminology", "terminology_errors"),
        ("Message Argument Errors", "argument_errors"),
        ("Forbidden Semantic Hardcodes", "semantic_hardcodes"),
    ):
        print()
        print(f"## {heading}")
        values = result[field]
        if not values:
            print("- NONE")
        else:
            for value in values:
                print(f"- {value}")
    print()
    print("## Non-Catalog Domain Data")
    if not result["domain_text_values"]:
        print("- NONE")
    else:
        for producer, node_id, value in result["domain_text_values"]:
            print(f"- {producer}:{node_id}:{value}")
    incomplete = any(result[field] for field in (
        "missing_messages", "missing_states", "blank_captions", "technical_echo", "terminology_errors",
        "argument_errors", "semantic_hardcodes",
    ))
    print()
    print(f"VERDICT={'MARKETCORE_STAGE6_I18N_AUDIT_INCOMPLETE' if incomplete else 'MARKETCORE_STAGE6_I18N_COMPLETE'}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()
    result = audit()
    _print_report(result)
    incomplete = any(result[field] for field in (
        "missing_messages", "missing_states", "blank_captions", "technical_echo", "terminology_errors",
        "argument_errors", "semantic_hardcodes",
    ))
    return 2 if args.enforce and incomplete else 0


if __name__ == "__main__":
    raise SystemExit(main())
