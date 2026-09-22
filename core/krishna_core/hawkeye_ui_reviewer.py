from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import re

from .vision_adapter import VisionAdapter


class HawkeyeUIReviewer:
    """Local perceptual reviewer for rendered application screenshots.

    Hawkeye is evidence-only here: it can surface visual defects but cannot override
    deterministic DOM, browser, accessibility or release gates.
    """

    def __init__(self, vision: VisionAdapter | None=None, max_images: int=12):
        self.vision=vision or VisionAdapter()
        self.max_images=max(1,min(int(max_images),24))

    def status(self) -> dict[str,Any]:
        state=self.vision.status()
        return {
            "name":"HAWKEYE UI REVIEWER",
            "available":bool(state.get("available")),
            "vision":state,
            "max_images":self.max_images,
            "authority":"perceptual evidence only; deterministic gates remain authoritative",
        }

    @staticmethod
    def _json_object(text: str) -> dict[str,Any]:
        raw=str(text or "").strip()
        candidates=[raw]
        if "```" in raw:
            for part in raw.split("```"):
                p=part.strip()
                if p.lower().startswith("json"):p=p[4:].strip()
                if p.startswith("{") and p.endswith("}"):candidates.append(p)
        if "{" in raw and "}" in raw:
            candidates.append(raw[raw.find("{"):raw.rfind("}")+1])
        for candidate in candidates:
            try:
                obj=json.loads(candidate)
                if isinstance(obj,dict):return obj
            except Exception:
                continue
        return {}

    @staticmethod
    def _content_type(path: Path) -> str:
        suffix=path.suffix.lower()
        return {".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".webp":"image/webp"}.get(suffix,"")

    @staticmethod
    def _normalize_issue(row: Any, image: str) -> dict[str,Any] | None:
        if not isinstance(row,dict):return None
        severity=str(row.get("severity") or "notice").strip().lower()
        if severity not in {"notice","warning","error","critical"}:severity="notice"
        confidence=row.get("confidence",0.0)
        try:confidence=max(0.0,min(float(confidence),1.0))
        except Exception:confidence=0.0
        detail=str(row.get("detail") or row.get("finding") or "").strip()[:1200]
        if not detail:return None
        return {
            "kind":str(row.get("kind") or "visual_observation")[:120],
            "detail":detail,
            "severity":severity,
            "confidence":confidence,
            "image":image,
        }

    def review(self, screenshots: list[dict[str,Any]], deterministic_context: dict[str,Any] | None=None,
               required: bool=False) -> dict[str,Any]:
        state=self.status()
        if not state["available"]:
            return {
                "available":False,"required":bool(required),"passed":not required,
                "reason":"local_vision_model_unavailable","status":state,"reviews":[],"issues":[],
            }

        rows=[];seen=set()
        for row in screenshots or []:
            path=Path(str(row.get("path") or row.get("screenshot") or "")).resolve()
            if not path.is_file() or path in seen:continue
            ctype=self._content_type(path)
            if not ctype:continue
            seen.add(path)
            rows.append({
                "path":str(path),"label":str(row.get("label") or row.get("url") or row.get("width") or path.name)[:300],
                "content_type":ctype,
            })
            if len(rows)>=self.max_images:break

        if not rows:
            return {
                "available":True,"required":bool(required),"passed":not required,
                "reason":"no_screenshots","reviews":[],"issues":[],
            }

        context=json.dumps(deterministic_context or {},ensure_ascii=False,default=str)[:12000]
        reviews=[];issues=[]
        for row in rows:
            prompt=(
                "You are HAWKEYE UI REVIEWER, an independent perceptual QA specialist. "
                "Inspect only visible UI evidence in this screenshot. Look for clipping, overlap, broken or missing assets, "
                "unreadable text, poor contrast that is visually obvious, malformed controls, inconsistent alignment/spacing, "
                "unexpected blank regions, broken responsive layout, accidental duplicate elements, or hierarchy problems. "
                "Do not claim backend/functionality failures from appearance. Do not reject a design merely because of subjective style taste. "
                "Use the supplied deterministic evidence only as context/corroboration. "
                "Return STRICT JSON only: "
                '{"passed":true,"summary":"...","issues":[{"kind":"...","detail":"...","severity":"notice|warning|error|critical","confidence":0.0}]}. '
                f"Screenshot label: {row['label']}. Deterministic context: {context}"
            )
            try:
                analysis=self.vision.analyze_bytes(Path(row["path"]).read_bytes(),row["content_type"],prompt)
                obj=self._json_object(analysis.get("analysis") or "")
                parsed=bool(obj)
                item_issues=[]
                for issue in obj.get("issues") or []:
                    norm=self._normalize_issue(issue,row["path"])
                    if norm:
                        item_issues.append(norm);issues.append(norm)
                reviews.append({
                    "image":row["path"],"label":row["label"],"parsed":parsed,
                    "provider":analysis.get("provider"),"model":analysis.get("model"),
                    "summary":str(obj.get("summary") or "")[:1600],
                    "reported_passed":obj.get("passed") if parsed else None,
                    "issues":item_issues,
                })
            except Exception as exc:
                reviews.append({
                    "image":row["path"],"label":row["label"],"parsed":False,
                    "error":f"{type(exc).__name__}: {exc}","issues":[],
                })

        material=[x for x in issues if x["severity"] in {"error","critical"} and x["confidence"]>=0.80]
        parse_failures=sum(1 for x in reviews if not x.get("parsed"))
        passed=not material and (not required or parse_failures==0)
        return {
            "available":True,"required":bool(required),"passed":passed,
            "review_count":len(reviews),"parse_failures":parse_failures,
            "material_issues":material,"issues":issues,"reviews":reviews,
            "policy":"high-confidence error/critical findings can block when Hawkeye review participates; subjective style preference never blocks",
        }
