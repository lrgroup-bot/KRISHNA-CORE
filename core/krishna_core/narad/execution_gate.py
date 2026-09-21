from __future__ import annotations
from contextlib import contextmanager
from threading import BoundedSemaphore,RLock
import os,time


class BoundedExecutionGate:
    """Resource-light concurrency guard; no worker pool and no extra daemon."""

    def __init__(self,max_concurrent=None,acquire_timeout=1.0):
        configured=max_concurrent if max_concurrent is not None else os.getenv("KRISHNA_NARAD_MAX_CONCURRENT","2")
        self.max_concurrent=max(1,min(int(configured),8))
        self.acquire_timeout=max(0.05,float(acquire_timeout))
        self._sem=BoundedSemaphore(self.max_concurrent)
        self._lock=RLock()
        self.active=0
        self.total=0
        self.rejected=0
        self.last_duration_ms=0

    @contextmanager
    def slot(self):
        if not self._sem.acquire(timeout=self.acquire_timeout):
            with self._lock:self.rejected+=1
            raise RuntimeError("NARAD busy: bounded workflow concurrency reached")
        started=time.perf_counter()
        with self._lock:
            self.active+=1;self.total+=1
        try:
            yield
        finally:
            elapsed=int((time.perf_counter()-started)*1000)
            with self._lock:
                self.active=max(0,self.active-1);self.last_duration_ms=elapsed
            self._sem.release()

    def status(self):
        with self._lock:
            return {
                "max_concurrent":self.max_concurrent,"active":self.active,
                "total_runs":self.total,"rejected_busy":self.rejected,
                "last_duration_ms":self.last_duration_ms,
                "policy":"bounded in-process execution; no extra worker pool",
            }
