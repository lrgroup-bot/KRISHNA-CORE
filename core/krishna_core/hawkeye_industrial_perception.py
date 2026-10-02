from __future__ import annotations
from typing import Any

def clamp(v):
    try:return max(0.0,min(1.0,float(v)))
    except Exception:return 0.0

class HawkeyeIndustrialOCRPolicy:
    """Local-first OCR routing for labels, screens, PCBs, plates and machinery markings."""
    @staticmethod
    def plan(*,quality=.8,tiny_text=False,industrial=False,screen=False):
        q=clamp(quality)
        if q<.35:return {"route":"mobile_recovery","actions":["focus","zoom","exposure","multi-frame"],"heavy_model":False}
        if tiny_text or industrial:return {"route":"pp_ocr_v6_tiny_or_small","reason":"small/industrial text","heavy_model":False}
        if screen:return {"route":"pp_ocr_v6_small","reason":"screen/digital text","heavy_model":False}
        return {"route":"pp_ocr_v6_small","reason":"OCR before semantic VLM","heavy_model":False}

class HawkeyeEquipmentChangeVerifier:
    """Compare equipment/object state while refusing viewpoint-only changes as verified."""
    IGNORED={"at","timestamp","updated_at","confidence","bbox","tracking_id"}
    @classmethod
    def compare(cls,previous:dict[str,Any],current:dict[str,Any],*,viewpoint_compatible=False):
        p=dict(previous or {});c=dict(current or {});changes=[]
        for key in sorted(set(p)|set(c)):
            if key not in cls.IGNORED and p.get(key)!=c.get(key):
                changes.append({"field":key,"before":p.get(key),"after":c.get(key)})
        confidence=min(clamp(p.get("confidence",.7)),clamp(c.get("confidence",.7)))
        if not viewpoint_compatible:confidence*=.55
        return {"schema":"hawkeye.equipment-change.v1","changed":bool(changes),"changes":changes[:64],
                "confidence":round(confidence,4),"viewpoint_compatible":bool(viewpoint_compatible),
                "verification_required":bool(changes and not viewpoint_compatible)}

class HawkeyeSensorPoseEvidence:
    """Normalize phone IMU/camera/depth evidence without claiming solved SLAM pose."""
    @staticmethod
    def normalize(sensor_context:dict[str,Any],camera=None,depth=None):
        s=dict(sensor_context or {});camera=dict(camera or {});depth=dict(depth or {})
        imu={"accel":s.get("accel") or s.get("accelerometer"),"gyro":s.get("gyro") or s.get("gyroscope"),
             "quaternion":s.get("quaternion") or s.get("rotation_quaternion"),"accuracy":s.get("sensor_accuracy")}
        return {"schema":"hawkeye.sensor-pose-evidence.v1","imu":imu,
                "camera":{"intrinsics":camera.get("intrinsics"),"pose":camera.get("pose"),"frame_id":camera.get("frame_id")},
                "depth":{"available":bool(depth),"source":depth.get("source"),"scale_known":bool(depth.get("scale_known"))},
                "fusion_ready":bool(imu["gyro"] and imu["quaternion"]),
                "metric_claim_allowed":bool(depth and depth.get("scale_known"))}

class HawkeyeReconstructionRouter:
    """Keep mapping/reconstruction engines replaceable and outside KRISHNA authority."""
    @staticmethod
    def plan(*,live=False,imu=False,gpu_vram_gb=0):
        if live and imu:return {"route":"visual_inertial_adapter","boundary":"external process/API","core_copy":False}
        if float(gpu_vram_gb or 0)>=8:return {"route":"gpu_reconstruction_adapter","boundary":"isolated worker","core_copy":False}
        return {"route":"offline_photogrammetry_adapter","boundary":"isolated worker","core_copy":False}
