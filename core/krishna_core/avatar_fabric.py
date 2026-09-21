from __future__ import annotations
class AvatarFabric:
    """Body and face provider registry; providers are loaded only when configured."""
    BODY=("anigen","poseforge","motius")
    FACE=("musetalk","liveportrait","liveavatar")
    def status(self): return {"body_providers":list(self.BODY),"face_providers":list(self.FACE),"mode":"provider_adapter"}
