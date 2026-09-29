from __future__ import annotations

from dataclasses import dataclass,asdict


@dataclass(frozen=True)
class SocialChannel:
    name:str
    mode:str
    capabilities:tuple[str,...]
    mutating:tuple[str,...]
    def as_dict(self):
        row=asdict(self);row["capabilities"]=list(self.capabilities);row["mutating"]=list(self.mutating);return row


class SocialChannelRegistry:
    """Truth registry for KRISHNA's owner-authorized social presence."""

    def __init__(self):
        rows=(
            SocialChannel("whatsapp","narad_direct",("inbox","draft","send","reply"),("send","reply")),
            SocialChannel("gmail","narad_direct",("search","read","triage","draft","send","label","trash"),("send","label","trash")),
            SocialChannel("instagram","connector_required",("inbox","analytics","draft","publish","reply"),("publish","reply")),
            SocialChannel("facebook_page","connector_required",("inbox","analytics","draft","publish","reply"),("publish","reply")),
            SocialChannel("linkedin","connector_required",("analytics","draft","publish","reply"),("publish","reply")),
            SocialChannel("x","connector_required",("analytics","draft","publish","reply"),("publish","reply")),
            SocialChannel("youtube","connector_required",("analytics","draft","publish","reply"),("publish","reply")),
            SocialChannel("metricool","optional_unified_connector",("analytics","schedule","draft","publish"),("schedule","publish")),
            SocialChannel("windsor_ai","optional_unified_connector",("analytics","campaign_read","supported_write"),("supported_write",)),
        )
        self._items={x.name:x for x in rows}

    def get(self,name):
        key=str(name or "").strip().lower()
        if key not in self._items:raise KeyError(key)
        return self._items[key].as_dict()

    def list(self):return [self._items[k].as_dict() for k in sorted(self._items)]

    def status(self):
        return {
            "component":"KRISHNA Social Channel Registry",
            "channels":self.list(),
            "connection_state":"provider/account connection is external and must be verified before action",
            "writes_require_superhuman_policy":True,
        }
