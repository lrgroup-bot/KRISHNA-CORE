from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path


DEFAULT_VIEWPORTS = (
    {"name": "desktop-xl", "width": 1920, "height": 1080},
    {"name": "desktop", "width": 1440, "height": 900},
    {"name": "tablet", "width": 1024, "height": 768},
    {"name": "mobile", "width": 390, "height": 844},
)
STATES = ("stable", "candidate", "experimental", "rejected")


@dataclass
class GUIEntry:
    id: str
    name: str
    project: str
    url: str
    state: str
    created_at: float
    updated_at: float
    latest_evaluation: dict | None = None
    notes: str = ""


class UIGuardianRegistry:
    """Persistent GUI registry: Stable / Candidate / Experimental / Rejected."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.entries: dict[str, GUIEntry] = {}
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8-sig"))
            self.entries = {
                row["id"]: GUIEntry(**row)
                for row in raw.get("entries", [])
                if isinstance(row, dict) and row.get("id")
            }
        except Exception:
            self.entries = {}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": 1,
            "states": list(STATES),
            "entries": [asdict(x) for x in self.entries.values()],
        }
        fd, temp = tempfile.mkstemp(prefix="ui-guardian-", suffix=".json", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as h:
                json.dump(payload, h, ensure_ascii=False, indent=2)
            os.replace(temp, self.path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    def list(self, project: str | None = None) -> dict:
        rows = [asdict(x) for x in self.entries.values()]
        if project:
            rows = [x for x in rows if x["project"] == project]
        rows.sort(key=lambda x: x["updated_at"], reverse=True)
        return {"states": list(STATES), "entries": rows, "count": len(rows)}

    def register(self, name: str, project: str, url: str, state: str = "candidate", notes: str = "") -> dict:
        state = str(state).lower().strip()
        if state not in STATES:
            raise ValueError(f"invalid GUI registry state: {state}")
        name = str(name or "").strip()
        url = str(url or "").strip()
        if not name or not url:
            raise ValueError("name and url are required")
        now = time.time()
        item = GUIEntry(
            id=str(uuid.uuid4()), name=name, project=str(project or "KRISHNA"),
            url=url, state=state, created_at=now, updated_at=now, notes=str(notes or "")[:2000],
        )
        self.entries[item.id] = item
        self._save()
        return asdict(item)

    def set_evaluation(self, entry_id: str, evaluation: dict) -> dict:
        item = self.entries.get(entry_id)
        if not item:
            raise KeyError("GUI registry entry not found")
        item.latest_evaluation = dict(evaluation)
        item.updated_at = time.time()
        self._save()
        return asdict(item)

    def transition(self, entry_id: str, target: str, verified: bool = False, notes: str = "") -> dict:
        item = self.entries.get(entry_id)
        if not item:
            raise KeyError("GUI registry entry not found")
        target = str(target).lower().strip()
        if target not in STATES:
            raise ValueError(f"invalid GUI registry state: {target}")
        if target == "stable":
            evaluation = item.latest_evaluation or {}
            if not verified or not evaluation.get("passed"):
                raise PermissionError("Stable promotion requires a passed UI Guardian evaluation and independent verification")
        item.state = target
        item.updated_at = time.time()
        if notes:
            item.notes = str(notes)[:2000]
        self._save()
        return asdict(item)


class UIGuardian:
    """Objective UI inspection across the KRISHNA viewport acceptance matrix."""

    def __init__(self, browser_operator, registry: UIGuardianRegistry, screenshot_root: str | Path):
        self.browser = browser_operator
        self.registry = registry
        self.screenshot_root = Path(screenshot_root)

    @staticmethod
    def _defects(report: dict, viewport: dict) -> list[dict]:
        defects = []
        for finding in report.get("findings") or []:
            defects.append({
                "viewport": viewport["name"],
                "kind": finding.get("kind", "browser_finding"),
                "severity": finding.get("severity", "error"),
                "detail": finding.get("detail", ""),
            })
        layout = report.get("layout") or {}
        if layout.get("horizontal_overflow"):
            defects.append({
                "viewport": viewport["name"],
                "kind": "horizontal_overflow",
                "severity": "error",
                "detail": f"scrollWidth={layout.get('scroll_width')} viewportWidth={layout.get('viewport_width')}",
            })
        if layout.get("document_height", 0) <= 0 or layout.get("document_width", 0) <= 0:
            defects.append({
                "viewport": viewport["name"],
                "kind": "empty_document_layout",
                "severity": "critical",
                "detail": "document has no measurable layout",
            })
        return defects

    def evaluate(self, project: str, url: str, viewports=None) -> dict:
        rows = list(viewports or DEFAULT_VIEWPORTS)
        run_id = str(uuid.uuid4())
        target = self.screenshot_root / run_id
        target.mkdir(parents=True, exist_ok=True)
        reports = []
        defects = []
        for viewport in rows:
            shot = target / f"{viewport['name']}.png"
            try:
                report = self.browser.inspect(
                    url,
                    screenshot_path=str(shot),
                    viewport={"width": int(viewport["width"]), "height": int(viewport["height"])},
                )
                reports.append({"viewport": dict(viewport), "report": report})
                defects.extend(self._defects(report, viewport))
            except Exception as exc:
                report = {
                    "url": url,
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "screenshot": None,
                }
                reports.append({"viewport": dict(viewport), "report": report})
                defects.append({
                    "viewport": viewport["name"],
                    "kind": "inspection_error",
                    "severity": "critical",
                    "detail": report["error"],
                })
        passed = not any(x.get("severity") in {"error", "critical"} for x in defects)
        return {
            "run_id": run_id,
            "project": str(project or "KRISHNA"),
            "url": url,
            "viewports": rows,
            "reports": reports,
            "defects": defects,
            "passed": passed,
            "evaluated_at": time.time(),
            "acceptance": "objective-browser-contracts",
        }

    def evaluate_entry(self, entry_id: str) -> dict:
        item = self.registry.entries.get(entry_id)
        if not item:
            raise KeyError("GUI registry entry not found")
        result = self.evaluate(item.project, item.url)
        self.registry.set_evaluation(entry_id, result)
        return result
