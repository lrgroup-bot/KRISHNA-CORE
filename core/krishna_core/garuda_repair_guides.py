"""Original offline repair-guide library for GARUDA; no third-party guide content."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
import json
import re

def _id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", value):
        raise ValueError("invalid identifier")
    return value

def _text(value, limit=4000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("invalid text")
    return value.strip()

@dataclass(frozen=True)
class GuideStep:
    title: str
    instruction: str
    safety_note: str = ""
    tool_ids: tuple[str, ...] = ()
    part_ids: tuple[str, ...] = ()
    media_refs: tuple[str, ...] = ()
    verification: str = ""
    requires_approval: bool = False

@dataclass(frozen=True)
class RepairGuide:
    guide_id: str
    device_model: str
    title: str
    difficulty: str
    estimated_minutes: int
    steps: tuple[GuideStep, ...]
    source: str
    license: str
    version: int = 1
    status: str = "draft"

def create_guide(device_model, title, difficulty, estimated_minutes, steps, *, source="original", license="first-party", version=1):
    _text(device_model, 160)
    _text(title, 200)
    if difficulty not in {"easy", "moderate", "difficult", "expert"}:
        raise ValueError("invalid difficulty")
    if type(estimated_minutes) is not int or not (1 <= estimated_minutes <= 10080):
        raise ValueError("invalid estimate")
    steps = tuple(steps)
    if not (1 <= len(steps) <= 200) or not all(isinstance(x, GuideStep) for x in steps):
        raise ValueError("invalid steps")
    for step in steps:
        _text(step.title, 200)
        _text(step.instruction)
        for item in step.tool_ids + step.part_ids + step.media_refs:
            _id(item)
    _text(source, 512)
    _text(license, 128)
    if type(version) is not int or version < 1:
        raise ValueError("invalid version")
    payload={"device_model":device_model,"title":title,"difficulty":difficulty,"estimated_minutes":estimated_minutes,
             "steps":[asdict(s) for s in steps],"source":source,"license":license,"version":version}
    digest=sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return RepairGuide("grg_"+digest[:24],device_model,title,difficulty,estimated_minutes,steps,source,license,version)

def save_guide(guide: RepairGuide, root):
    """Immutable versioned artifact: no overwrites or network calls."""
    root=Path(root)
    root.mkdir(parents=True,exist_ok=True)
    path=root/(guide.guide_id+".json")
    with path.open("x",encoding="utf-8") as file:
        json.dump(asdict(guide),file,ensure_ascii=False,indent=2)
        file.write("\n")
    return path

def guide_summary(guide: RepairGuide):
    return {"guide_id":guide.guide_id,"model":guide.device_model,"difficulty":guide.difficulty,
            "steps":len(guide.steps),"estimated_minutes":guide.estimated_minutes,"status":guide.status}
