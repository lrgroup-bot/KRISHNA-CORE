from __future__ import annotations
class CreatorRuntime:
    """Capability registry for ComfyUI/Wan/LTX/SkyReels style creator workers."""
    def __init__(self,workers): self.workers=workers
    def status(self): return {"mode":"on_demand","providers":["comfyui","wan","ltx","skyreels"],"workers":self.workers.status()}
