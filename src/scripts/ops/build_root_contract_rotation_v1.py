# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import re
import subprocess


SERVICE = "finam-paper-pipeline.service"


def load_execstart() -> str:
    out = subprocess.check_output(["systemctl", "cat", SERVICE], text=True)
    lines = [x.strip() for x in out.splitlines() if x.strip().startswith("ExecStart=")]
    if not lines:
        raise SystemExit("ExecStart not found")
    return lines[-1].replace("ExecStart=", "", 1)


def dedupe_symbols(symbols: list[str]) -> list[str]:
    result = []
    seen = set()
    for s in symbols:
        if s and s not in seen:
            result.append(s)
            seen.add(s)
    return result


def replace_symbols(execstart: str, br: str, ng: str) -> str:
    # Русский комментарий: основной root-symbol Brent всегда переводим на новый BR.
    execstart = re.sub(r"--symbol\s+\S+", f"--symbol {br}", execstart)

    m = re.search(r"--symbols\s+([^\s]+)", execstart)
    if not m:
        return execstart

    old_symbols = m.group(1).split(",")
    new_symbols = []

    for s in old_symbols:
        if re.match(r"^BR[A-Z]\d@RTSX$", s):
            new_symbols.append(br)
        elif re.match(r"^NG[A-Z]\d@RTSX$", s):
            new_symbols.append(ng)
        else:
            new_symbols.append(s)

    new_symbols = dedupe_symbols(new_symbols)

    # Русский комментарий: гарантируем наличие обоих root-контрактов.
    for required in [br, ng]:
        if required not in new_symbols:
            new_symbols.insert(0, required)

    return execstart[: m.start(1)] + ",".join(new_symbols) + execstart[m.end(1):]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--br", default="BRQ6@RTSX")
    p.add_argument("--ng", default="NGN6@RTSX")
    args = p.parse_args()

    old_exec = load_execstart()
    new_exec = replace_symbols(old_exec, args.br, args.ng)

    print("[Service]")
    print("ExecStart=")
    print(f"ExecStart={new_exec}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
