#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib
from collections import defaultdict


INTENT_FILE = pathlib.Path(
    "/tmp/strategy_owner_intent_points_v1/"
    "owner_candidates.tsv"
)

FAMILY_FILE = pathlib.Path(
    "/tmp/strategy_owner_family_classification_v1/"
    "primary_candidates.tsv"
)

BINDING_FILE = pathlib.Path(
    "/tmp/strategy_runtime_binding_discovery_v2/"
    "candidate_binding_summary.tsv"
)

CONSTRUCTOR_FILE = pathlib.Path(
    "/tmp/strategy_runtime_binding_discovery_v2/"
    "constructor_sites.tsv"
)

BINDING_SITES_FILE = pathlib.Path(
    "/tmp/strategy_runtime_binding_discovery_v2/"
    "binding_sites.tsv"
)

OUTPUT_DIR = pathlib.Path(
    "/tmp/strategy_owner_confirmation_v1"
)

CONFIRMED_FILE = (
    OUTPUT_DIR / "confirmed_strategy_owners.tsv"
)

ALTERNATIVE_FILE = (
    OUTPUT_DIR / "alternative_strategy_candidates.tsv"
)

FAMILY_OWNERSHIP_FILE = (
    OUTPUT_DIR / "strategy_family_ownership.tsv"
)

CONTRACT_FILE = (
    OUTPUT_DIR / "strategy_owner_contract.txt"
)

UNRESOLVED_FILE = (
    OUTPUT_DIR / "unresolved.tsv"
)

# Подтверждение строится только на уже доказанных runtime-контурах.
#
# BR:
# основной runtime использует закрытый signal bar и
# BrConservativeBreakout.on_signal_bar.
#
# NG:
# текущий NG M1 runtime-контур использует
# NgConservativeBreakoutM1.on_signal_bar.
# Остальные NG реализации считаются альтернативными до отдельного
# доказательства их включения в основной runtime.
#
# EQUITY:
# обе стратегии являются допустимыми strategy-family owners,
# поскольку family работает по multi-strategy модели.
CONFIRMATION_POLICY = {
    "BR": {
        "ownership_model": "SINGLE_ACTIVE_OWNER",
        "confirmed": {
            "BrConservativeBreakout.on_signal_bar",
        },
    },
    "NG": {
        "ownership_model": "SINGLE_ACTIVE_OWNER",
        "confirmed": {
            "NgConservativeBreakoutM1.on_signal_bar",
        },
    },
    "EQUITY": {
        "ownership_model": "MULTI_STRATEGY_FAMILY",
        "confirmed": {
            "VolatilityBreakoutEquity.on_quote",
            "MeanReversionEquity.on_quote",
        },
    },
}

EXPECTED_FAMILIES = {
    "BR",
    "NG",
    "EQUITY",
}


def read_tsv(
    path: pathlib.Path,
) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(
            f"source_file_missing:{path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as stream:
        return [
            {
                key: str(value or "").strip()
                for key, value in row.items()
            }
            for row in csv.DictReader(
                stream,
                delimiter="\t",
            )
        ]


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: list[dict[str, object]],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def int_value(
    row: dict[str, str],
    field: str,
) -> int:
    value = row.get(field, "0")

    try:
        return int(value)
    except ValueError:
        return 0


def main() -> int:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    intent_rows = read_tsv(INTENT_FILE)
    family_rows = read_tsv(FAMILY_FILE)
    binding_rows = read_tsv(BINDING_FILE)
    constructor_rows = read_tsv(CONSTRUCTOR_FILE)
    binding_site_rows = read_tsv(
        BINDING_SITES_FILE
    )

    intent_index = {
        row["qualified_name"]: row
        for row in intent_rows
    }

    binding_index = {
        row["candidate_symbol"]: row
        for row in binding_rows
    }

    constructor_count_by_class: dict[str, int] = (
        defaultdict(int)
    )

    for row in constructor_rows:
        constructor_count_by_class[
            row["class_name"]
        ] += 1

    binding_site_count_by_class: dict[str, int] = (
        defaultdict(int)
    )

    for row in binding_site_rows:
        binding_site_count_by_class[
            row["class_name"]
        ] += 1

    confirmed: list[dict[str, object]] = []
    alternatives: list[dict[str, object]] = []
    unresolved: list[dict[str, object]] = []

    family_candidates: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    for row in family_rows:
        family_candidates[
            row["family"]
        ].append(row)

    for family in sorted(EXPECTED_FAMILIES):
        policy = CONFIRMATION_POLICY.get(family)

        if policy is None:
            unresolved.append(
                {
                    "family": family,
                    "candidate_symbol": "",
                    "reason": (
                        "CONFIRMATION_POLICY_MISSING"
                    ),
                }
            )
            continue

        candidates = family_candidates.get(
            family,
            [],
        )

        if not candidates:
            unresolved.append(
                {
                    "family": family,
                    "candidate_symbol": "",
                    "reason": (
                        "NO_FAMILY_CANDIDATES"
                    ),
                }
            )
            continue

        confirmed_symbols = set(
            policy["confirmed"]
        )

        discovered_symbols = {
            row["qualified_name"]
            for row in candidates
        }

        missing_confirmed = (
            confirmed_symbols
            - discovered_symbols
        )

        for symbol in sorted(missing_confirmed):
            unresolved.append(
                {
                    "family": family,
                    "candidate_symbol": symbol,
                    "reason": (
                        "EXPECTED_CONFIRMED_"
                        "CANDIDATE_NOT_DISCOVERED"
                    ),
                }
            )

        for candidate in candidates:
            symbol = candidate["qualified_name"]
            class_name = candidate["class_name"]

            intent = intent_index.get(symbol)
            binding = binding_index.get(symbol)

            if intent is None:
                unresolved.append(
                    {
                        "family": family,
                        "candidate_symbol": symbol,
                        "reason": (
                            "INTENT_EVIDENCE_MISSING"
                        ),
                    }
                )
                continue

            if binding is None:
                unresolved.append(
                    {
                        "family": family,
                        "candidate_symbol": symbol,
                        "reason": (
                            "BINDING_EVIDENCE_MISSING"
                        ),
                    }
                )
                continue

            signal_constructor_count = int_value(
                intent,
                "constructor_count",
            )
            positive_signal_return_count = (
                int_value(
                    intent,
                    "positive_signal_return_count",
                )
            )
            absence_return_count = int_value(
                intent,
                "absence_return_count",
            )
            downstream_side_effect_count = (
                int_value(
                    intent,
                    "downstream_side_effect_count",
                )
            )
            binding_evidence_count = int_value(
                binding,
                "evidence_count",
            )

            has_trade_intent = int(
                signal_constructor_count > 0
                or positive_signal_return_count > 0
            )

            has_no_signal_contract = int(
                absence_return_count > 0
            )

            has_binding_evidence = int(
                binding_evidence_count > 0
            )

            no_downstream_side_effects = int(
                downstream_side_effect_count == 0
            )

            evidence_complete = int(
                has_trade_intent == 1
                and has_binding_evidence == 1
                and no_downstream_side_effects == 1
            )

            base_row = {
                "family": family,
                "ownership_model": policy[
                    "ownership_model"
                ],
                "owner_path": candidate["path"],
                "owner_class": class_name,
                "owner_method": candidate[
                    "function"
                ],
                "owner_symbol": symbol,
                "trade_intent_evidence": (
                    has_trade_intent
                ),
                "no_signal_contract": (
                    has_no_signal_contract
                ),
                "binding_evidence": (
                    has_binding_evidence
                ),
                "constructor_site_count": (
                    constructor_count_by_class[
                        class_name
                    ]
                ),
                "binding_site_count": (
                    binding_site_count_by_class[
                        class_name
                    ]
                ),
                "downstream_side_effect_count": (
                    downstream_side_effect_count
                ),
                "evidence_complete": (
                    evidence_complete
                ),
                "runtime_instrumentation": 0,
            }

            if symbol in confirmed_symbols:
                if not evidence_complete:
                    unresolved.append(
                        {
                            "family": family,
                            "candidate_symbol": symbol,
                            "reason": (
                                "CONFIRMED_OWNER_"
                                "EVIDENCE_INCOMPLETE"
                            ),
                        }
                    )
                    continue

                confirmed.append(
                    {
                        **base_row,
                        "classification": (
                            "CONFIRMED_STRATEGY_OWNER"
                        ),
                        "owner_confirmed": 1,
                    }
                )
            else:
                alternatives.append(
                    {
                        **base_row,
                        "classification": (
                            "ALTERNATIVE_OR_SHADOW_"
                            "STRATEGY"
                        ),
                        "owner_confirmed": 0,
                        "reason": (
                            "BINDING_PRESENT_BUT_NOT_"
                            "PRIMARY_RUNTIME_OWNER"
                        ),
                    }
                )

    confirmed.sort(
        key=lambda row: (
            str(row["family"]),
            str(row["owner_symbol"]),
        )
    )

    alternatives.sort(
        key=lambda row: (
            str(row["family"]),
            str(row["owner_symbol"]),
        )
    )

    family_rows_out: list[
        dict[str, object]
    ] = []

    for family in sorted(EXPECTED_FAMILIES):
        family_confirmed = [
            row
            for row in confirmed
            if row["family"] == family
        ]

        family_alternatives = [
            row
            for row in alternatives
            if row["family"] == family
        ]

        model = str(
            CONFIRMATION_POLICY[family][
                "ownership_model"
            ]
        )

        if model == "SINGLE_ACTIVE_OWNER":
            model_valid = int(
                len(family_confirmed) == 1
            )
        elif model == "MULTI_STRATEGY_FAMILY":
            model_valid = int(
                len(family_confirmed) >= 2
            )
        else:
            model_valid = 0

        if not model_valid:
            unresolved.append(
                {
                    "family": family,
                    "candidate_symbol": "",
                    "reason": (
                        "OWNERSHIP_MODEL_CARDINALITY_"
                        "VIOLATION"
                    ),
                }
            )

        family_rows_out.append(
            {
                "family": family,
                "ownership_model": model,
                "confirmed_owner_count": len(
                    family_confirmed
                ),
                "confirmed_symbols": ",".join(
                    str(row["owner_symbol"])
                    for row in family_confirmed
                ),
                "alternative_candidate_count": len(
                    family_alternatives
                ),
                "alternative_symbols": ",".join(
                    str(row["owner_symbol"])
                    for row in family_alternatives
                ),
                "ownership_model_valid": (
                    model_valid
                ),
                "runtime_instrumentation": 0,
            }
        )

    confirmed_fields = (
        "family",
        "ownership_model",
        "owner_path",
        "owner_class",
        "owner_method",
        "owner_symbol",
        "trade_intent_evidence",
        "no_signal_contract",
        "binding_evidence",
        "constructor_site_count",
        "binding_site_count",
        "downstream_side_effect_count",
        "evidence_complete",
        "classification",
        "owner_confirmed",
        "runtime_instrumentation",
    )

    write_tsv(
        CONFIRMED_FILE,
        confirmed_fields,
        confirmed,
    )

    write_tsv(
        ALTERNATIVE_FILE,
        (
            *confirmed_fields,
            "reason",
        ),
        alternatives,
    )

    write_tsv(
        FAMILY_OWNERSHIP_FILE,
        (
            "family",
            "ownership_model",
            "confirmed_owner_count",
            "confirmed_symbols",
            "alternative_candidate_count",
            "alternative_symbols",
            "ownership_model_valid",
            "runtime_instrumentation",
        ),
        family_rows_out,
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "family",
            "candidate_symbol",
            "reason",
        ),
        unresolved,
    )

    with CONTRACT_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write(
            "STRATEGY OWNER CONTRACT V1\n"
        )
        stream.write(
            "==========================\n\n"
        )

        for row in family_rows_out:
            stream.write(
                f"{row['family']}_MODEL="
                f"{row['ownership_model']}\n"
            )
            stream.write(
                f"{row['family']}_OWNERS="
                f"{row['confirmed_symbols']}\n"
            )
            stream.write(
                f"{row['family']}_ALTERNATIVES="
                f"{row['alternative_symbols']}\n"
            )

        stream.write("\n")
        stream.write(
            f"CONFIRMED_OWNER_COUNT="
            f"{len(confirmed)}\n"
        )
        stream.write(
            f"ALTERNATIVE_CANDIDATE_COUNT="
            f"{len(alternatives)}\n"
        )
        stream.write(
            f"UNRESOLVED_COUNT="
            f"{len(unresolved)}\n"
        )
        stream.write(
            "RUNTIME_INSTRUMENTATION=0\n"
        )

    print(
        "=== BUILD STRATEGY OWNER "
        "CONFIRMATION V1 ==="
    )
    print(
        f"confirmed_strategy_owner_count="
        f"{len(confirmed)}"
    )
    print(
        f"alternative_strategy_candidate_count="
        f"{len(alternatives)}"
    )
    print(
        f"family_ownership_count="
        f"{len(family_rows_out)}"
    )
    print(
        f"unresolved_count="
        f"{len(unresolved)}"
    )

    for row in family_rows_out:
        print(
            f"FAMILY_OWNERSHIP "
            f"family={row['family']} "
            f"model={row['ownership_model']} "
            f"confirmed={row['confirmed_owner_count']} "
            f"owners={row['confirmed_symbols']} "
            f"alternatives="
            f"{row['alternative_candidate_count']}"
        )

    for row in confirmed:
        print(
            f"CONFIRMED_STRATEGY_OWNER "
            f"family={row['family']} "
            f"symbol={row['owner_symbol']} "
            f"model={row['ownership_model']}"
        )

    for row in alternatives:
        print(
            f"ALTERNATIVE_STRATEGY "
            f"family={row['family']} "
            f"symbol={row['owner_symbol']}"
        )

    print("owner_assignment_performed=1")
    print("writes_performed=0")
    print("db_writes_performed=0")
    print("runtime_instrumentation=0")
    print("strategy_changed=0")
    print("risk_engine_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "STRATEGY_OWNER_CONFIRMATION_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
