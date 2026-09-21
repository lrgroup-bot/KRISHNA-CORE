from __future__ import annotations
class RevenueEngine:
    """Business adapter layer; never owns KRISHNA reasoning or credentials."""
    def __init__(self,bus): self.bus=bus
    def status(self): return {"crm":"twenty_adapter","publishing":"postiz_adapter","analytics":"adapter","authority":"business_layer_only"}
