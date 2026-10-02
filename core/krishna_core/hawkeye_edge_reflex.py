from __future__ import annotations
import time
from typing import Any

class HawkeyeEdgeReflex:
    """Normalize cheap edge-camera events before heavier HAWKEYE reasoning."""

    def __init__(self,min_confidence:float=.35):
        self.min_confidence=float(min_confidence)
        self.last_event=None

    @staticmethod
    def _bbox(value):
        if not isinstance(value,(list,tuple)) or len(value)!=4:return None
        try:
            out=[max(0.0,min(1.0,float(x))) for x in value]
        except Exception:return None
        return out if out[2]>0 and out[3]>0 else None

    def ingest(self,event:dict[str,Any])->dict[str,Any]:
        row=dict(event or {})
        confidence=max(0.0,min(1.0,float(row.get("confidence") or 0.0)))
        bbox=self._bbox(row.get("bbox"))
        accepted=bool(bbox and confidence>=self.min_confidence)
        out={
            "schema":"hawkeye.edge-reflex.v1","accepted":accepted,
            "source":str(row.get("source") or "edge-camera"),
            "tracking_id":row.get("tracking_id"),"class":str(row.get("class") or row.get("label") or "object"),
            "confidence":confidence,"bbox":bbox,"timestamp":float(row.get("timestamp") or time.time()),
            "event":str(row.get("event") or "track_update"),
            "heavy_reasoning_required":bool(row.get("novel") or row.get("ambiguous") or not accepted),
            "camera_follow_hint":self.follow_hint(bbox) if accepted else None,
            "actuation_scope":"camera framing only",
        }
        self.last_event=out
        return out

    @staticmethod
    def follow_hint(bbox):
        if not bbox:return None
        cx=bbox[0]+bbox[2]/2;cy=bbox[1]+bbox[3]/2
        dx=round(cx-.5,4);dy=round(cy-.5,4)
        return {"offset_x":dx,"offset_y":dy,"centered":abs(dx)<.06 and abs(dy)<.06}

    def status(self):
        return {"ready":True,"min_confidence":self.min_confidence,"last_event":self.last_event,
                "supported_reference":"ESP-WHO/ByteTrack-style metadata bridge","stores_raw_video":False}
