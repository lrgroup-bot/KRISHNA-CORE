from __future__ import annotations

import threading
import time


class NaradScheduler:
    """Small daemon scheduler for durable Narad schedule triggers."""

    def __init__(self,runtime,poll_seconds=15):
        self.runtime=runtime
        self.poll_seconds=max(5,int(poll_seconds))
        self._stop=threading.Event()
        self._thread=None

    def start(self):
        if self._thread and self._thread.is_alive():return self.status()
        self._stop.clear()
        self._thread=threading.Thread(target=self._loop,name="narad-scheduler",daemon=True)
        self._thread.start()
        return self.status()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():self._thread.join(timeout=2)
        return self.status()

    def _loop(self):
        while not self._stop.wait(self.poll_seconds):
            try:self.runtime.run_due()
            except Exception:pass

    def status(self):
        return {"running":bool(self._thread and self._thread.is_alive()),"poll_seconds":self.poll_seconds}
