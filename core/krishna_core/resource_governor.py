from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, asdict
from threading import BoundedSemaphore, RLock
import os
import time


@dataclass
class ResourceSnapshot:
    active_jobs: int
    max_concurrent_jobs: int
    cpu_budget_percent: int
    memory_budget_percent: int
    timestamp: float
    cpu_percent: float | None = None
    memory_percent: float | None = None
    pressure: str = "unknown"


class ResourceGovernor:
    """Lightweight concurrency/resource policy guard for autonomous work."""

    def __init__(self, max_concurrent_jobs: int | None = None,
                 cpu_budget_percent: int | None = None,
                 memory_budget_percent: int | None = None):
        self.max_jobs = max(1, max_concurrent_jobs or int(os.getenv("KRISHNA_MAX_JOBS", "2")))
        self.cpu_budget = min(100, max(1, cpu_budget_percent or int(os.getenv("KRISHNA_CPU_BUDGET", "60"))))
        self.memory_budget = min(100, max(1, memory_budget_percent or int(os.getenv("KRISHNA_MEMORY_BUDGET", "70"))))
        self._slots = BoundedSemaphore(self.max_jobs)
        self._lock = RLock()
        self._active = 0
        self._last_cpu=None
        self._last_memory=None

    def measure_pressure(self):
        cpu=memory=None
        try:
            import psutil
            cpu=float(psutil.cpu_percent(interval=0.05));memory=float(psutil.virtual_memory().percent)
        except Exception:
            pass
        with self._lock:self._last_cpu,self._last_memory=cpu,memory
        over=(cpu is not None and cpu>=self.cpu_budget) or (memory is not None and memory>=self.memory_budget)
        return {"cpu_percent":cpu,"memory_percent":memory,"over_budget":over}

    @contextmanager
    def job(self, timeout: float = 0):
        pressure=self.measure_pressure()
        if pressure["over_budget"]:
            raise RuntimeError("resource governor pressure limit reached")
        acquired = self._slots.acquire(timeout=timeout)
        if not acquired:
            raise RuntimeError("resource governor busy")
        with self._lock:
            self._active += 1
        try:
            yield
        finally:
            with self._lock:
                self._active -= 1
            self._slots.release()

    def snapshot(self) -> dict:
        with self._lock:
            return asdict(ResourceSnapshot(
                active_jobs=self._active,
                max_concurrent_jobs=self.max_jobs,
                cpu_budget_percent=self.cpu_budget,
                memory_budget_percent=self.memory_budget,
                timestamp=time.time(),cpu_percent=self._last_cpu,memory_percent=self._last_memory,
                pressure=("over_budget" if ((self._last_cpu is not None and self._last_cpu>=self.cpu_budget) or (self._last_memory is not None and self._last_memory>=self.memory_budget)) else "within_budget" if self._last_cpu is not None or self._last_memory is not None else "unknown"),
            ))
