"""SUDARSHAN: evidence-based, permission-gated application reconstruction planner.

This module only prepares a plan. It does not execute third-party apps,
extract protected content, bypass controls, or install analysis tools.
"""
from dataclasses import dataclass
from typing import Iterable

SUPPORTED = {"website", "desktop", "android", "ios", "source"}
PROHIBITED = {"credentials", "private_data", "proprietary_assets", "license_bypass", "drm_bypass", "unauthorized_api"}
STAGES = ("intake", "permission_review", "observe", "feature_inventory", "design", "independent_build", "test", "human_review")

@dataclass(frozen=True)
class ReconstructionRequest:
    reference: str
    platform: str
    authorized: bool
    requested_features: tuple[str, ...]
    excluded_material: tuple[str, ...] = ()

def create_plan(request: ReconstructionRequest):
    if not isinstance(request, ReconstructionRequest):
        raise TypeError("ReconstructionRequest required")
    if not request.reference.strip():
        raise ValueError("reference required")
    if request.platform not in SUPPORTED:
        raise ValueError("unsupported platform")
    if not request.authorized:
        raise PermissionError("owner authorization or lawful analysis basis required")
    features = tuple(dict.fromkeys(x.strip() for x in request.requested_features if x.strip()))
    if not features:
        raise ValueError("at least one feature required")
    exclusions = set(request.excluded_material) | PROHIBITED
    return {
        "engine": "SUDARSHAN",
        "reference": request.reference,
        "platform": request.platform,
        "stages": list(STAGES),
        "features": [{"name": name, "status": "not_tested", "evidence": None} for name in features],
        "excluded_material": sorted(exclusions),
        "implementation": "independent",
        "execution_enabled": False,
        "release_ready": False,
    }
