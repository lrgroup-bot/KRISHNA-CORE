from __future__ import annotations
class AvatarProductionGate:
 REQUIRED_VISEMES={"aa","ee","ih","oh","ou"}
 REQUIRED_CLIPS={"idle","listen","think","speak","walk","flute","dhyan","sleep","wake"}
 def inspect_manifest(self,m):
  skins=int(m.get("skins",0));joints=int(m.get("joints",0));animations=set(m.get("animation_names") or [])
  morphs={str(x).lower() for x in (m.get("morph_target_names") or [])}
  rigged=skins>0 and joints>0
  visemes=self.REQUIRED_VISEMES.issubset(morphs)
  clips=self.REQUIRED_CLIPS.issubset({x.lower() for x in animations})
  talking_ready=bool(rigged and visemes and "speak" in {x.lower() for x in animations})
  return {"static_avatar_allowed":int(m.get("meshes",0))>0,"rigged":rigged,"visemes_ready":visemes,
   "required_clips_ready":clips,"talking_ready":talking_ready,
   "production_ready":bool(rigged and visemes and clips),
   "missing":{"rig":not rigged,"visemes":sorted(self.REQUIRED_VISEMES-morphs),
              "clips":sorted(self.REQUIRED_CLIPS-{x.lower() for x in animations})}}
