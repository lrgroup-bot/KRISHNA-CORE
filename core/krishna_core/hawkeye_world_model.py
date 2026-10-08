from __future__ import annotations
from dataclasses import dataclass,asdict
from typing import Any
import math,time

def _clip(v): return max(0.0,min(1.0,float(v or 0.0)))
def _center(b):
    if not isinstance(b,(list,tuple)) or len(b)!=4:return None
    return (float(b[0])+float(b[2])/2,float(b[1])+float(b[3])/2)

@dataclass
class TargetFingerprint:
    label:str=""
    colors:tuple[str,...]=()
    attributes:tuple[str,...]=()
    mask_signature:str|None=None
    depth:float|None=None
    point_count:int=0
    trajectory:tuple[float,float]|None=None
    updated_at:float=0.0
    def as_dict(self):
        row=asdict(self);row["colors"]=list(self.colors);row["attributes"]=list(self.attributes);return row

class HawkeyeWorldModel:
    """Session-local target/world evidence. Stores descriptors, never a real-world identity."""
    def __init__(self): self.targets={};self.scene={}
    def observe(self,key,candidate:dict[str,Any]):
        attrs=candidate.get("attributes") or {};colors=attrs.get("colors") or ([attrs.get("upper_color")] if attrs.get("upper_color") else [])
        terms=[]
        for k,v in attrs.items():
            if isinstance(v,(list,tuple,set)):terms.extend(map(str,v))
            elif v is not None:terms.extend((str(k),str(v)))
        fp=TargetFingerprint(
            label=str(candidate.get("class") or candidate.get("label") or ""),
            colors=tuple(dict.fromkeys(str(x).lower() for x in colors if x)),
            attributes=tuple(dict.fromkeys(x.lower() for x in terms)),
            mask_signature=candidate.get("mask_signature"),
            depth=None if candidate.get("depth") is None else float(candidate["depth"]),
            point_count=int(candidate.get("point_count") or len(candidate.get("point_anchors") or [])),
            trajectory=_center(candidate.get("bbox")),updated_at=time.time())
        self.targets[str(key)]=fp;return fp.as_dict()
    def compare(self,key,candidate):
        fp=self.targets.get(str(key))
        if not fp:return {"score":0.0,"signals":{}}
        attrs=" ".join(map(str,(candidate.get("attributes") or {}).values())).lower()
        color=max([1.0 if c in attrs else 0.0 for c in fp.colors] or [0.0])
        mask=1.0 if fp.mask_signature and fp.mask_signature==candidate.get("mask_signature") else 0.0
        depth=0.0
        if fp.depth is not None and candidate.get("depth") is not None:
            depth=max(0.0,1.0-abs(fp.depth-float(candidate["depth"]))/max(.1,abs(fp.depth)))
        motion=0.0;c=_center(candidate.get("bbox"))
        if fp.trajectory and c:
            motion=max(0.0,1.0-math.dist(fp.trajectory,c)/.5)
        point=_clip(candidate.get("point_consistency"))
        reid=_clip(candidate.get("reid_similarity"))
        signals={"appearance":reid,"color":color,"mask":mask,"depth":depth,"motion":motion,"points":point}
        score=.32*reid+.16*color+.14*mask+.12*depth+.12*motion+.14*point
        return {"score":round(score,4),"signals":signals}

class HawkeyePerceptionScheduler:
    """Escalate perception only when cheap evidence is insufficient."""
    TIERS=("REFLEX","VISION","DEEP_VISION","GEOMETRY_3D")
    def __init__(self,hardware=None):
        self.hardware=dict(hardware or {})
    def choose(self,*,confidence=1.0,ambiguous=False,occluded=False,needs_mask=False,needs_depth=False,
               needs_small_object=False,needs_3d=False,commercial=True):
        confidence=_clip(confidence)
        reasons=[]
        if needs_3d:
            tier="GEOMETRY_3D";reasons.append("3d_geometry_requested")
        elif ambiguous or needs_mask or needs_small_object or confidence<.45:
            tier="DEEP_VISION";reasons.append("semantic_or_precision_escalation")
        elif occluded or needs_depth or confidence<.72:
            tier="VISION";reasons.append("temporal_or_depth_escalation")
        else:tier="REFLEX";reasons.append("cheap_tracking_sufficient")
        vram=float(self.hardware.get("vram_gb") or 0)
        backends={
          "REFLEX":["edge_reflex","native_tracker"],
          "VISION":["bot_sort_or_native_reid","depth_anything_v2_small","point_memory_adapter"],
          "DEEP_VISION":["grounding_dino_local","sam2_or_mobile_sam","sahi_if_tiny_objects","point_memory_adapter"],
          "GEOMETRY_3D":["vggt_commercial_checkpoint"] if vram>=6 else ["defer_3d_backend"],
        }[tier]
        if commercial and tier=="VISION":
            backends=[x for x in backends if x!="cotracker3"]
        return {"tier":tier,"backends":backends,"reasons":reasons,"vram_gb":vram,"local_first":True}

class HawkeyeVisionCapabilityRegistry:
    """License/hardware gate. Adapters remain optional until separately installed and benchmarked."""
    CAPABILITIES={
      "sam2":{"role":"video masks/multi-object segmentation","license":"Apache-2.0","commercial":True,"load":"heavy"},
      "mobile_sam_v2":{"role":"lightweight segmentation/ONNX candidate","license_check_required":True,"commercial":None,"load":"medium"},
      "grounding_dino":{"role":"text-conditioned open-vocabulary acquisition","license_check_required":True,"commercial":None,"load":"heavy"},
      "tapnext_pp":{"role":"long point tracks/occlusion/re-detection","license":"Apache-2.0","commercial":True,"load":"heavy"},
      "cotracker3":{"role":"dense/online point tracking","license":"CC-BY-NC-majority","commercial":False,"load":"heavy"},
      "depth_anything_v2_small":{"role":"relative/metric-depth adapter candidate","license":"Apache-2.0","commercial":True,"load":"medium"},
      "depth_anything_v2_large":{"role":"larger depth backend","license":"CC-BY-NC-4.0","commercial":False,"load":"heavy"},
      "vggt_commercial":{"role":"camera/depth/point-map/3D reconstruction","license":"commercial checkpoint required; military excluded","commercial":True,"load":"very-heavy"},
      "vggt_omega":{"role":"newer sequence camera/depth reconstruction","license_check_required":True,"commercial":None,"load":"very-heavy"},
      "sahi":{"role":"sliced high-resolution tiny-object inference","license_check_required":True,"commercial":None,"load":"scheduler"},
    }
    @classmethod
    def eligible(cls,*,commercial=True):
        out={}
        for k,v in cls.CAPABILITIES.items():
            row=dict(v)
            row["eligible"]=not commercial or row.get("commercial") is True
            if commercial and row.get("commercial") is None:row["eligible"]=False;row["reason"]="license_review_required"
            elif commercial and row.get("commercial") is False:row["reason"]="noncommercial_model_or_code"
            out[k]=row
        return out
