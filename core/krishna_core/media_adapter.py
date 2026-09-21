from __future__ import annotations
class OpenMontageAdapter:
    """Boundary only: OpenMontage belongs to the media/YouTube worker, not KRISHNA's brain."""
    def __init__(self,worker_fabric,worker_name="openmontage"): self.workers=worker_fabric; self.worker_name=worker_name
    def available(self): return self.worker_name in self.workers.workers
    def status(self): return {"provider":"openmontage","available":self.available(),"placement":"media-worker"}
    def start(self):
        if not self.available(): raise RuntimeError("OpenMontage worker is not registered")
        return self.workers.start(self.worker_name)
