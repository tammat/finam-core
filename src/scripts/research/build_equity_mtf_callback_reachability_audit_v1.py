#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import os


ROOT = Path(os.getenv("FINAM_CORE_ROOT", "/opt/finam-core"))

TARGET_FILES = [
    Path("src/finam_core/pipelines/paper_pipeline.py"),
    Path("src/finam_core/data/mtf_aggregator.py"),
    Path("src/finam_core/data/market_data.py"),
    Path("src/finam_core/data/market_data_service.py"),
    Path("src/finam_core/data/moex_market_data.py"),
    Path("src/finam_core/adapters/grpc/market_data.py"),
    Path("adapters/grpc/market_data.py"),
]

TERMS = [
    "_on_quote",
    "MTFBarAggregator",
    "on_closed_bar",
    "PIPE_MTF_BAR_CLOSED",
    "_process_br_closed_bar_for_paper_signal",
    "_process_ng_m1_closed_bar_for_paper_signal",
    "_process_equity_closed_bar_for_paper_signal",
    "market_bars",
    "save_market_bar",
    "log_market_bar",
    "SBER@MISX",
    "@MISX",
]


def read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return path.read_text(errors="replace").splitlines()
    except FileNotFoundError:
        return []


def emit_context(path: Path, lines: list[str], line_no: int, radius: int = 5) -> None:
    start = max(1, line_no - radius)
    end = min(len(lines), line_no + radius)
    for current in range(start, end + 1):
        code = lines[current - 1].strip()
        print(
            "EQUITY_MTF_CALLBACK_CONTEXT "
            f"file={path} line={current} code={code}"
        )


def main() -> int:
    print("=== EQUITY MTF CALLBACK REACHABILITY AUDIT V1 ===")
    print("mode=read_only")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("db_update=0")
    print(f"root={ROOT}")

    hits: list[tuple[str, int, str, str]] = []

    for rel_path in TARGET_FILES:
        path = ROOT / rel_path
        lines = read_lines(path)
        if not lines:
            continue

        for i, line in enumerate(lines, start=1):
            for term in TERMS:
                if term in line:
                    hits.append((str(rel_path), i, term, line.strip()))

    print()
    print("EQUITY_MTF_CALLBACK_CODE_HITS")
    for file_name, line_no, term, code in hits:
        print(
            "EQUITY_MTF_CALLBACK_CODE_HIT "
            f"file={file_name} line={line_no} term={term} code={code}"
        )

        if term in {
            "_on_quote",
            "MTFBarAggregator",
            "on_closed_bar",
            "PIPE_MTF_BAR_CLOSED",
            "_process_br_closed_bar_for_paper_signal",
            "_process_ng_m1_closed_bar_for_paper_signal",
            "_process_equity_closed_bar_for_paper_signal",
            "market_bars",
        }:
            emit_context(ROOT / file_name, read_lines(ROOT / file_name), line_no)

    paper_hits = [h for h in hits if h[0].endswith("paper_pipeline.py")]
    mtf_hits = [h for h in hits if "mtf_aggregator.py" in h[0]]
    callback_hits = [h for h in hits if h[2] in {"on_closed_bar", "PIPE_MTF_BAR_CLOSED"}]
    equity_handler_hits = [h for h in hits if h[2] == "_process_equity_closed_bar_for_paper_signal"]
    br_ng_handler_hits = [
        h for h in hits
        if h[2] in {"_process_br_closed_bar_for_paper_signal", "_process_ng_m1_closed_bar_for_paper_signal"}
    ]
    market_bar_writer_hits = [
        h for h in hits
        if h[2] in {"market_bars", "save_market_bar", "log_market_bar"}
    ]

    print()
    print("EQUITY_MTF_CALLBACK_REACHABILITY_AUDIT_SUMMARY")
    print(f"files_with_hits={len(set(h[0] for h in hits))}")
    print(f"hits_total={len(hits)}")
    print(f"paper_pipeline_hits={len(paper_hits)}")
    print(f"mtf_aggregator_hits={len(mtf_hits)}")
    print(f"callback_hits={len(callback_hits)}")
    print(f"equity_handler_hits={len(equity_handler_hits)}")
    print(f"br_ng_handler_hits={len(br_ng_handler_hits)}")
    print(f"market_bar_writer_hits={len(market_bar_writer_hits)}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")

    if br_ng_handler_hits and not equity_handler_hits:
        print("VERDICT=EQUITY_HANDLER_MISSING_IN_MTF_CALLBACK")
    elif equity_handler_hits and callback_hits:
        print("VERDICT=EQUITY_HANDLER_EXISTS_CALLBACK_REVIEW_REQUIRED")
    elif market_bar_writer_hits and not callback_hits:
        print("VERDICT=MARKET_BARS_WRITTEN_WITHOUT_VISIBLE_CALLBACK")
    else:
        print("VERDICT=EQUITY_MTF_CALLBACK_REACHABILITY_REVIEW_REQUIRED")

    print("EQUITY_MTF_CALLBACK_REACHABILITY_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
