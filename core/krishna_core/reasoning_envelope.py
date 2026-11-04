from __future__ import annotations
def reasoning_envelope(answer,*,confidence,evidence=None,conflicts=None,assumptions=None,verification_required=False):
 c=max(0.0,min(1.0,float(confidence)))
 return {"answer":answer,"confidence":c,"evidence":list(evidence or []),"conflicts":list(conflicts or []),
 "assumptions":list(assumptions or []),"verification_required":bool(verification_required or c<0.75)}
