from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import json
import re
import time


_UI_MODES = {"research_abcd", "reference", "describe", "existing", "none"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value or "").strip()).strip("-._")
    if not text:
        raise ValueError("project is required")
    return text[:96]


@dataclass(frozen=True)
class Enhancement:
    id: str
    title: str
    benefit: str
    complexity: str
    estimated_minutes: float
    rationale: str
    priority: str = "optional"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProjectGenesis:
    """Owner-first project intake and scope-lock governor.

    Genesis is intentionally state-only: it never writes project source. It makes
    the owner decisions explicit before SoftwareFactory/HR/MRITYUNJAY can begin
    implementation.
    """

    SCHEMA = "krishna.project-genesis.v1"

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, project: str) -> Path:
        return self.root / (_slug(project) + ".json")

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeError(f"project genesis state is unreadable: {type(exc).__name__}") from exc
        if not isinstance(value, dict):
            raise RuntimeError("project genesis state must be an object")
        return value

    def _read(self, project: str) -> dict[str, Any]:
        path = self._path(project)
        if not path.exists():
            raise KeyError(project)
        return self._load_json(path)

    def _write(self, state: dict[str, Any]) -> dict[str, Any]:
        state = dict(state)
        state["updated_at"] = _now()
        path = self._path(state["project"])
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(path)
        return state

    def start(self, project: str, goal: str) -> dict[str, Any]:
        project = str(project or "").strip()
        goal = str(goal or "").strip()
        if not project or not goal:
            raise ValueError("project and goal are required")
        path = self._path(project)
        if path.exists():
            current = self._load_json(path)
            if current.get("scope_locked") and current.get("goal") != goal:
                raise RuntimeError("project scope is already locked; create a change request instead")
            if current.get("goal") != goal:
                current["goal"] = goal
                self._write(current)
            return self.status(project)
        state = {
            "schema": self.SCHEMA,
            "project": project,
            "goal": goal,
            "phase": "INTAKE",
            "created_at": _now(),
            "updated_at": _now(),
            "scope_locked": False,
            "mission_id": None,
            "intake": {
                "deadline_hours": None,
                "deadline_at": None,
                "platforms": [],
                "core_requirements": [],
                "ui_mode": None,
                "ui_reference": "",
                "ui_description": "",
                "owner_notes": "",
            },
            "enhancements": {"proposals": [], "selected_ids": [], "decided": False, "research_evidence": []},
            "design": {"required": False, "session_id": None, "candidate_id": None, "label": None},
            "goal_contract": None,
        }
        self._write(state)
        return self.status(project)

    @staticmethod
    def _deadline_ready(intake: dict[str, Any]) -> bool:
        hours = intake.get("deadline_hours")
        if hours is not None:
            try:
                if float(hours) > 0:
                    return True
            except (TypeError, ValueError):
                pass
        return bool(str(intake.get("deadline_at") or "").strip())

    @classmethod
    def missing_intake(cls, intake: dict[str, Any]) -> list[str]:
        missing = []
        if not cls._deadline_ready(intake):
            missing.append("timeline")
        if not [x for x in intake.get("platforms") or [] if str(x).strip()]:
            missing.append("platforms")
        if not [x for x in intake.get("core_requirements") or [] if str(x).strip()]:
            missing.append("core_requirements")
        mode = str(intake.get("ui_mode") or "").strip().lower()
        if mode not in _UI_MODES:
            missing.append("ui_direction")
        elif mode == "reference" and not str(intake.get("ui_reference") or "").strip():
            missing.append("ui_reference")
        elif mode == "describe" and not str(intake.get("ui_description") or "").strip():
            missing.append("ui_description")
        return missing

    def update_intake(
        self, project: str, *, deadline_hours: float | None = None, deadline_at: str | None = None,
        platforms: Iterable[str] | None = None, core_requirements: Iterable[str] | None = None,
        ui_mode: str | None = None, ui_reference: str | None = None,
        ui_description: str | None = None, owner_notes: str | None = None,
    ) -> dict[str, Any]:
        state = self._read(project)
        if state.get("scope_locked"):
            raise RuntimeError("scope is locked; use Idea Intake/change control")
        intake = dict(state.get("intake") or {})
        if deadline_hours is not None:
            value = float(deadline_hours)
            if value <= 0:
                raise ValueError("deadline_hours must be positive")
            intake["deadline_hours"] = value
        if deadline_at is not None:
            raw_deadline = str(deadline_at).strip()
            intake["deadline_at"] = raw_deadline or None
            if raw_deadline and deadline_hours is None:
                try:
                    target = datetime.fromisoformat(raw_deadline.replace("Z", "+00:00"))
                    if target.tzinfo is None:
                        target = target.replace(tzinfo=datetime.now().astimezone().tzinfo)
                    hours = (target - datetime.now(target.tzinfo)).total_seconds() / 3600.0
                except ValueError as exc:
                    raise ValueError("deadline_at must be ISO-8601 when deadline_hours is omitted") from exc
                if hours <= 0:
                    raise ValueError("deadline_at must be in the future")
                intake["deadline_hours"] = hours
        if platforms is not None:
            intake["platforms"] = list(dict.fromkeys(str(x).strip() for x in platforms if str(x).strip()))
        if core_requirements is not None:
            intake["core_requirements"] = list(dict.fromkeys(str(x).strip() for x in core_requirements if str(x).strip()))
        if ui_mode is not None:
            mode = str(ui_mode).strip().lower()
            if mode not in _UI_MODES:
                raise ValueError("unsupported ui_mode")
            intake["ui_mode"] = mode
        if ui_reference is not None:
            intake["ui_reference"] = str(ui_reference).strip()
        if ui_description is not None:
            intake["ui_description"] = str(ui_description).strip()
        if owner_notes is not None:
            intake["owner_notes"] = str(owner_notes).strip()
        state["intake"] = intake
        state["design"]["required"] = intake.get("ui_mode") == "research_abcd"
        state["phase"] = "ENHANCEMENT_RESEARCH" if not self.missing_intake(intake) else "INTAKE"
        self._write(state)
        return self.status(project)

    @staticmethod
    def _baseline_enhancements(intake: dict[str, Any]) -> list[Enhancement]:
        platforms = " ".join(intake.get("platforms") or []).lower()
        req = " ".join(intake.get("core_requirements") or []).lower()
        out = [
            Enhancement("quality-observability", "Operational health and error evidence", "high", "low", 35,
                        "Makes failures diagnosable and gives KRISHNA evidence for self-heal.", "recommended"),
            Enhancement("security-privacy", "Security/privacy acceptance gates", "high", "medium", 50,
                        "Prevents credentials, permissions and data handling from becoming late-stage defects.", "recommended"),
            Enhancement("backup-recovery", "Backup/export and recovery path", "high", "medium", 45,
                        "Protects user/project data and gives Project Perfection a recovery target.", "recommended"),
            Enhancement("accessibility", "Accessibility and responsive-state coverage", "medium", "low", 30,
                        "Improves usability and adds objective UI acceptance criteria.", "recommended"),
        ]
        if any(x in platforms for x in ("android", "ios", "mobile")):
            out.append(Enhancement("offline-sync", "Offline-first queue and sync recovery", "high", "medium", 75,
                                   "Mobile connectivity is intermittent; queued sync prevents data loss.", "recommended"))
            out.append(Enhancement("device-acceptance", "Clean-install real-device acceptance", "high", "medium", 60,
                                   "A build is not complete until the installed app survives launch/restart/permissions.", "recommended"))
        if any(x in req for x in ("sale", "lead", "customer", "business", "order", "vehicle", "shop")):
            out.append(Enhancement("analytics", "Outcome/lead analytics", "medium", "medium", 55,
                                   "Makes business outcomes measurable without changing the core transaction flow.", "optional"))
        if any(x in req for x in ("admin", "login", "user", "account", "customer")):
            out.append(Enhancement("roles-audit", "Role-based access and audit history", "high", "medium", 70,
                                   "Separates owner/admin/customer permissions and records sensitive changes.", "recommended"))
        return out

    def propose_enhancements(
        self, project: str, *, research_evidence: Iterable[dict[str, Any]] | None = None,
        additional: Iterable[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        state = self._read(project)
        missing = self.missing_intake(state.get("intake") or {})
        if missing:
            raise RuntimeError("project intake incomplete: " + ",".join(missing))
        proposals = [x.as_dict() for x in self._baseline_enhancements(state["intake"])]
        seen = {x["id"] for x in proposals}
        for i, row in enumerate(additional or []):
            title = str(row.get("title") or "").strip()
            if not title:
                continue
            key = re.sub(r"[^a-z0-9]+", "-", str(row.get("id") or title).lower()).strip("-")[:64] or f"extra-{i+1}"
            if key in seen:
                continue
            seen.add(key)
            proposals.append({
                "id": key,
                "title": title,
                "benefit": str(row.get("benefit") or "unknown"),
                "complexity": str(row.get("complexity") or "unknown"),
                "estimated_minutes": float(row.get("estimated_minutes") or 30),
                "rationale": str(row.get("rationale") or ""),
                "priority": str(row.get("priority") or "optional"),
            })
        state["enhancements"] = {
            "proposals": proposals,
            "selected_ids": [],
            "decided": False,
            "research_evidence": list(research_evidence or [])[:30],
        }
        state["phase"] = "ENHANCEMENT_REVIEW"
        self._write(state)
        return self.status(project)

    def decide_enhancements(self, project: str, selected_ids: Iterable[str]) -> dict[str, Any]:
        state = self._read(project)
        proposals = list((state.get("enhancements") or {}).get("proposals") or [])
        if not proposals:
            raise RuntimeError("enhancement research/proposals must run before owner decision")
        valid = {str(x.get("id")) for x in proposals}
        chosen = list(dict.fromkeys(str(x).strip() for x in selected_ids if str(x).strip()))
        unknown = [x for x in chosen if x not in valid]
        if unknown:
            raise ValueError("unknown enhancement ids: " + ",".join(unknown))
        state["enhancements"]["selected_ids"] = chosen
        state["enhancements"]["decided"] = True
        state["phase"] = "DESIGN_REVIEW" if state["design"].get("required") else "SCOPE_REVIEW"
        self._write(state)
        return self.status(project)

    def record_design_selection(self, project: str, session_id: str, candidate_id: str, label: str | None = None) -> dict[str, Any]:
        state = self._read(project)
        if not state["design"].get("required"):
            raise RuntimeError("A/B/C/D design selection is not required for this project")
        if not str(session_id or "").strip() or not str(candidate_id or "").strip():
            raise ValueError("session_id and candidate_id are required")
        state["design"].update({
            "session_id": str(session_id).strip(),
            "candidate_id": str(candidate_id).strip(),
            "label": str(label or "").strip() or None,
        })
        state["phase"] = "SCOPE_REVIEW"
        self._write(state)
        return self.status(project)

    def lock_scope(self, project: str, acceptance: Iterable[str] | None = None, constraints: Iterable[str] | None = None) -> dict[str, Any]:
        state = self._read(project)
        if state.get("scope_locked") and state.get("goal_contract"):
            return self.status(project)
        missing = self.missing_intake(state.get("intake") or {})
        if missing:
            raise RuntimeError("project intake incomplete: " + ",".join(missing))
        if not state.get("enhancements", {}).get("decided"):
            raise RuntimeError("owner must accept/reject enhancement proposals before scope lock")
        if state.get("design", {}).get("required") and not state["design"].get("candidate_id"):
            raise RuntimeError("owner must select and submit an A/B/C/D design before scope lock")
        selected = set(state["enhancements"].get("selected_ids") or [])
        enhancement_rows = [x for x in state["enhancements"].get("proposals") or [] if x.get("id") in selected]
        conditions = list(dict.fromkeys(
            [str(x).strip() for x in state["intake"].get("core_requirements") or [] if str(x).strip()] +
            [str(x).strip() for x in acceptance or [] if str(x).strip()] +
            ["required tests pass", "security gate passes", "packaged artifact is installed and verified"]
        ))
        goal_contract = {
            "schema": "krishna.goal-contract.v1",
            "objective": state["goal"],
            "completion_conditions": conditions,
            "constraints": list(dict.fromkeys(str(x).strip() for x in constraints or [] if str(x).strip())),
            "platforms": list(state["intake"].get("platforms") or []),
            "deadline_hours": state["intake"].get("deadline_hours"),
            "deadline_at": state["intake"].get("deadline_at"),
            "selected_enhancements": enhancement_rows,
            "design_selection": dict(state.get("design") or {}),
            "owner_scope_locked": True,
            "locked_at": _now(),
        }
        state["goal_contract"] = goal_contract
        state["scope_locked"] = True
        state["phase"] = "READY_FOR_ARCHITECT_HR"
        self._write(state)
        return self.status(project)

    def bind_mission(self, project: str, mission_id: str) -> dict[str, Any]:
        state = self._read(project)
        value = str(mission_id or "").strip()
        if not value:
            raise ValueError("mission_id is required")
        existing = str(state.get("mission_id") or "").strip()
        if existing and existing != value:
            raise RuntimeError("Project Genesis is already bound to another mission")
        state["mission_id"] = value
        self._write(state)
        return self.status(project)

    def questions(self, project: str) -> list[dict[str, Any]]:
        state = self._read(project)
        missing = set(self.missing_intake(state.get("intake") or {}))
        rows = []
        if "timeline" in missing:
            rows.append({"field": "timeline", "question": "When do you need this project completed?"})
        if "platforms" in missing:
            rows.append({"field": "platforms", "question": "Which platforms should KRISHNA build: Android, iOS, PC/Web, server, or a combination?"})
        if "core_requirements" in missing:
            rows.append({"field": "core_requirements", "question": "Which features are mandatory for version 1?"})
        if "ui_direction" in missing:
            rows.append({"field": "ui_direction", "question": "Should KRISHNA research and show A/B/C/D UI designs, use a reference, improve an existing UI, or follow your description?"})
        if "ui_reference" in missing:
            rows.append({"field": "ui_reference", "question": "Which UI/reference should KRISHNA use as inspiration?"})
        if "ui_description" in missing:
            rows.append({"field": "ui_description", "question": "Describe how you want the UI to look and behave."})
        return rows

    def status(self, project: str) -> dict[str, Any]:
        state = self._read(project)
        missing = self.missing_intake(state.get("intake") or {})
        intake_ready = not missing
        enhancements = state.get("enhancements") or {}
        design = state.get("design") or {}
        if not intake_ready:
            next_action = "owner_answer_intake"
        elif not enhancements.get("proposals"):
            next_action = "project.genesis.enhancements"
        elif not enhancements.get("decided"):
            next_action = "owner_decide_enhancements"
        elif design.get("required") and not design.get("candidate_id"):
            next_action = "project.design.research"
        elif not state.get("scope_locked"):
            next_action = "project.genesis.lock_scope"
        else:
            next_action = "engineering.plan"
        return {
            **state,
            "intake_ready": intake_ready,
            "missing_intake": missing,
            "questions": self.questions(project) if missing else [],
            "implementation_allowed": bool(state.get("scope_locked") and state.get("goal_contract")),
            "next_action": next_action,
            "authority": "owner scope decision -> KRISHNA/Sudarshan -> HR/SoftwareFactory",
        }
