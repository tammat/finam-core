from __future__ import annotations

import subprocess
import sys
import time
import os
from dataclasses import dataclass

from finam_core.research.research_runtime_state_repository import (
    ResearchRuntimeStateRepository,
)


@dataclass(frozen=True)
class ResearchRuntimeSupervisorConfig:
    supervisor_name: str
    symbols: list[str]
    trade_source: str = "paper"
    interval_sec: int = 300
    limit: int = 20000
    once: bool = False
    sync_universe: bool = True


class ResearchRuntimeSupervisor:
    """
    Русский комментарий:
    Автономный supervisor research pipeline.
    Не исполняет сделки. Только обновляет research/governance состояние.
    """

    def __init__(
        self,
        config: ResearchRuntimeSupervisorConfig,
        repository: ResearchRuntimeStateRepository | None = None,
    ) -> None:
        self.config = config
        self.repository = repository or ResearchRuntimeStateRepository()

    def run(self) -> int:
        self.repository.migrate()

        self.repository.upsert_state(
            supervisor_name=self.config.supervisor_name,
            status="STARTED",
            active_symbols=",".join(self.config.symbols),
        )

        while True:
            rc = self.run_cycle()

            if self.config.once:
                return rc

            time.sleep(max(int(self.config.interval_sec), 1))

    def run_cycle(self) -> int:
        symbols_arg = ",".join(self.config.symbols)

        load_1m = os.getloadavg()[0]
        load_limit = max(1.0, float(os.getenv("RESEARCH_RUNTIME_MAX_LOAD_1M", "3.0")))
        if load_1m >= load_limit:
            reason = f"RESOURCE_GATE_LOAD_HIGH:{load_1m:.2f}>={load_limit:.2f}"
            self.repository.upsert_state(
                supervisor_name=self.config.supervisor_name,
                status="DEFERRED",
                active_symbols=symbols_arg,
                last_error=reason,
            )
            print(f"RESEARCH_RUNTIME_SUPERVISOR_DEFERRED reason={reason}", flush=True)
            return 0

        cycle_id = self.repository.start_cycle(
            supervisor_name=self.config.supervisor_name,
            symbols=symbols_arg,
            trade_source=self.config.trade_source,
        )

        started = time.monotonic()

        cmd = [
            sys.executable,
            "src/scripts/research_pipeline_orchestrator.py",
            "--symbols",
            symbols_arg,
            "--trade-source",
            self.config.trade_source,
            "--limit",
            str(self.config.limit),
        ]

        if self.config.sync_universe:
            cmd.append("--sync-universe")

        print(
            "RESEARCH_RUNTIME_SUPERVISOR_CYCLE_START "
            f"cycle_id={cycle_id} "
            f"symbols={symbols_arg} "
            f"trade_source={self.config.trade_source}",
            flush=True,
        )

        try:
            result = subprocess.run(cmd)
            rc = int(result.returncode)
            status = "OK" if rc == 0 else "FAILED"
            error_message = "" if rc == 0 else "orchestrator_failed"
        except Exception as exc:
            rc = 1
            status = "FAILED"
            error_message = str(exc)

        duration = round(time.monotonic() - started, 6)

        self.repository.finish_cycle(
            cycle_id=cycle_id,
            duration_sec=duration,
            return_code=rc,
            status=status,
            error_message=error_message,
        )

        self.repository.upsert_state(
            supervisor_name=self.config.supervisor_name,
            status=status,
            active_symbols=symbols_arg,
            failed_symbols="" if rc == 0 else symbols_arg,
            last_error=error_message,
            mark_success=(rc == 0),
        )

        print(
            "RESEARCH_RUNTIME_SUPERVISOR_CYCLE_DONE "
            f"cycle_id={cycle_id} "
            f"status={status} "
            f"rc={rc} "
            f"duration_sec={duration}",
            flush=True,
        )

        return rc
