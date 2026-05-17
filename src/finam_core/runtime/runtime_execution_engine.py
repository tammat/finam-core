import signal
import time
from datetime import datetime
from typing import Callable, Iterable, Optional

from finam_core.runtime.runtime_state import RuntimeWorkerState
from finam_core.runtime.runtime_telemetry import RuntimeTelemetry


class RuntimeExecutionEngine:
    """
    RuntimeExecutionEngine v3.

    Бесконечный supervisor-loop:
    - обновляет runtime-universe;
    - запускает новые worker;
    - останавливает отключённые worker;
    - пишет runtime telemetry;
    - корректно завершается по SIGINT/SIGTERM.
    """

    def __init__(
        self,
        universe_provider,
        telemetry: Optional[RuntimeTelemetry] = None,
        supervisor_interval_sec: float = 5.0,
        rebalance_interval_sec: float = 60.0,
        worker_runner: Optional[Callable[[str], object]] = None,
    ):
        self.universe_provider = universe_provider
        self.telemetry = telemetry
        self.supervisor_interval_sec = supervisor_interval_sec
        self.rebalance_interval_sec = rebalance_interval_sec
        self.worker_runner = worker_runner

        self.shutdown_requested = False
        self.workers: dict[str, object] = {}
        self.worker_states: dict[str, RuntimeWorkerState] = {}
        self.last_rebalance_at: Optional[float] = None

    def install_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, self.request_shutdown)
        signal.signal(signal.SIGTERM, self.request_shutdown)

    def request_shutdown(self, signum=None, frame=None) -> None:
        self.shutdown_requested = True

    def run_forever(self) -> None:
        self.install_signal_handlers()

        while not self.shutdown_requested:
            self.supervisor_tick()
            time.sleep(self.supervisor_interval_sec)

        self.stop_all_workers(reason="shutdown_requested")
        self.write_telemetry()

    def supervisor_tick(self) -> None:
        active_symbols = set(self.load_active_symbols())

        self.stop_disabled_workers(active_symbols)
        self.start_new_workers(active_symbols)
        self.rebalance_if_due()
        self.write_telemetry()

    def load_active_symbols(self) -> Iterable[str]:
        symbols = self.universe_provider.get_symbols()
        return list(symbols or [])

    def start_new_workers(self, active_symbols: set[str]) -> None:
        for symbol in sorted(active_symbols):
            if symbol in self.workers:
                continue

            worker = self.worker_runner(symbol) if self.worker_runner else None
            self.workers[symbol] = worker
            self.worker_states[symbol] = RuntimeWorkerState(
                symbol=symbol,
                enabled=True,
                status="running",
                started_at=datetime.utcnow(),
                last_heartbeat_at=datetime.utcnow(),
            )

            print(f"RUNTIME_WORKER_STARTED symbol={symbol}", flush=True)

    def stop_disabled_workers(self, active_symbols: set[str]) -> None:
        for symbol in sorted(list(self.workers.keys())):
            if symbol in active_symbols:
                self.worker_states[symbol].last_heartbeat_at = datetime.utcnow()
                continue

            self.stop_worker(symbol, reason="disabled_in_runtime_universe")

    def stop_worker(self, symbol: str, reason: str) -> None:
        worker = self.workers.pop(symbol, None)

        if hasattr(worker, "stop"):
            worker.stop()

        state = self.worker_states.get(symbol)
        if state is None:
            state = RuntimeWorkerState(symbol=symbol, enabled=False, status="stopped")

        state.enabled = False
        state.status = "stopped"
        state.stopped_at = datetime.utcnow()
        state.last_error = reason
        self.worker_states[symbol] = state

        print(f"RUNTIME_WORKER_STOPPED symbol={symbol} reason={reason}", flush=True)

    def stop_all_workers(self, reason: str) -> None:
        for symbol in sorted(list(self.workers.keys())):
            self.stop_worker(symbol, reason=reason)

    def rebalance_if_due(self) -> None:
        now = time.monotonic()

        if self.last_rebalance_at is None:
            self.last_rebalance_at = now
            print("RUNTIME_REBALANCE_INIT", flush=True)
            return

        if now - self.last_rebalance_at < self.rebalance_interval_sec:
            return

        self.last_rebalance_at = now
        print("RUNTIME_REBALANCE_DUE", flush=True)

    def write_telemetry(self) -> None:
        if self.telemetry is None:
            return

        self.telemetry.write_worker_states(self.worker_states.values())
