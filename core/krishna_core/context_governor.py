from __future__ import annotations
class ContextGovernor:
    """Keeps agent context bounded; stores references rather than repeatedly injecting full artifacts."""
    def __init__(self,max_items=24,max_chars=48000): self.max_items=max_items; self.max_chars=max_chars
    def select(self,items):
        chosen=[]; total=0
        for item in sorted(items,key=lambda x:(bool(x.get("verified")),float(x.get("score",0))),reverse=True):
            text=str(item.get("text",""))
            if len(chosen)>=self.max_items or total+len(text)>self.max_chars: continue
            chosen.append(item); total+=len(text)
        return chosen
