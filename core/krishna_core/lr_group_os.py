from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
import os
import shutil
import uuid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


ACTIVE_DEPARTMENTS = {
    "lr_commerce": "LR Commerce",
    "lr_sales": "LR Sales",
    "lr_hr": "LR HR",
    "lr_ca": "LR CA",
    "lr_legal": "LR Legal",
    "lr_technology": "LR Technology",
    "lr_production": "LR Production",
    "lr_advertisement": "LR Advertisement",
}

FROZEN_COMPANIES = {
    "lr_social_science": "LR Social Science",
    "lr_mines_minerals": "LR Mines & Minerals",
    "lr_fintech": "LR FinTech",
    "lrs_motors": "LRS Motors",
}

HIGH_IMPACT_ACTIONS = {
    "spend", "payment", "refund", "bank_write", "tax_file", "gst_file",
    "legal_file", "contract_sign", "employee_terminate", "external_publish",
    "external_message", "delete_record", "credential_change",
}


@dataclass(frozen=True)
class ActionDecision:
    status: str
    reason: str
    approval_required: bool
    department: str
    action: str


class LRGroupOS:
    """Local-first governed operating core for LR Group.

    This is deliberately backend-only. It provides canonical department/company
    boundaries, zero-spend enforcement, owner approval gates, append-only audit
    receipts and shared work-item routing. Frozen companies cannot execute work
    until the owner explicitly activates them in a future change.
    """

    SCHEMA = "lr.group.os.v1"

    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.backup = self.path.with_suffix(self.path.suffix + ".bak")
        if not self.path.exists():
            self._write(self._empty(), make_backup=False)

    @classmethod
    def _empty(cls) -> dict[str, Any]:
        return {
            "schema": cls.SCHEMA,
            "updated_at": _now(),
            "policy": {
                "zero_spend": True,
                "autonomous_spend_limit_inr": 0,
                "owner_approval_for_external_writes": True,
                "free_only_ai": True,
                "fail_closed": True,
            },
            "departments": [
                {"id": key, "name": name, "status": "active"}
                for key, name in ACTIVE_DEPARTMENTS.items()
            ],
            "companies": [
                {"id": key, "name": name, "status": "frozen", "reason": "awaiting_owner_idea"}
                for key, name in FROZEN_COMPANIES.items()
            ],
            "work_items": [],
            "approvals": [],
            "audit": [],
        }

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("schema") != self.SCHEMA:
                raise ValueError("schema mismatch")
            return data
        except Exception as exc:
            if self.backup.exists():
                data = json.loads(self.backup.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("schema") == self.SCHEMA:
                    self._write(data, make_backup=False)
                    return data
            raise RuntimeError(f"LR Group state unreadable: {type(exc).__name__}: {exc}") from exc

    def _write(self, data: dict[str, Any], *, make_backup: bool = True) -> None:
        data = dict(data)
        data["schema"] = self.SCHEMA
        data["updated_at"] = _now()
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        if make_backup and self.path.exists():
            try:
                shutil.copy2(self.path, self.backup)
            except OSError:
                pass
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)

    @staticmethod
    def _receipt_hash(event: dict[str, Any]) -> str:
        raw = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _audit(self, data: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        prior = data["audit"][-1]["hash"] if data["audit"] else "GENESIS"
        record = {"id": _id("audit"), "time": _now(), "previous_hash": prior, **event}
        record["hash"] = self._receipt_hash(record)
        data["audit"].append(record)
        return record

    def status(self) -> dict[str, Any]:
        data = self._read()
        return {
            "schema": self.SCHEMA,
            "policy": dict(data["policy"]),
            "departments": list(data["departments"]),
            "companies": list(data["companies"]),
            "open_work": sum(1 for x in data["work_items"] if x.get("status") not in {"done", "cancelled"}),
            "pending_approvals": sum(1 for x in data["approvals"] if x.get("status") == "pending"),
        }

    def decide(self, department: str, action: str, *, amount_inr: float = 0, external_write: bool = False) -> ActionDecision:
        department = str(department).strip().lower()
        action = str(action).strip().lower()
        if department in FROZEN_COMPANIES:
            return ActionDecision("blocked", "company_frozen_awaiting_owner_idea", False, department, action)
        if department not in ACTIVE_DEPARTMENTS:
            return ActionDecision("blocked", "unknown_department", False, department, action)
        if float(amount_inr or 0) > 0:
            return ActionDecision("approval", "zero_spend_policy", True, department, action)
        if action in HIGH_IMPACT_ACTIONS or external_write:
            return ActionDecision("approval", "owner_approval_required", True, department, action)
        return ActionDecision("allowed", "local_or_read_only_action", False, department, action)

    def submit_work(self, department: str, title: str, *, action: str = "internal_work", amount_inr: float = 0, external_write: bool = False, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        title = str(title).strip()
        if not title:
            raise ValueError("work title is required")
        decision = self.decide(department, action, amount_inr=amount_inr, external_write=external_write)
        data = self._read()
        item = {
            "id": _id("work"), "department": decision.department, "title": title,
            "action": decision.action, "amount_inr": round(float(amount_inr or 0), 2),
            "external_write": bool(external_write), "payload": dict(payload or {}),
            "status": "blocked" if decision.status == "blocked" else ("awaiting_approval" if decision.approval_required else "ready"),
            "created_at": _now(), "updated_at": _now(),
        }
        data["work_items"].append(item)
        approval = None
        if decision.approval_required:
            approval = {
                "id": _id("approval"), "work_id": item["id"], "status": "pending",
                "reason": decision.reason, "exact_action": decision.action,
                "exact_amount_inr": item["amount_inr"], "created_at": _now(),
            }
            data["approvals"].append(approval)
        self._audit(data, {"kind": "work_submitted", "work_id": item["id"], "decision": asdict(decision)})
        self._write(data)
        return {"work": item, "decision": asdict(decision), "approval": approval}

    def resolve_approval(self, approval_id: str, *, approved: bool, actor: str = "owner") -> dict[str, Any]:
        data = self._read()
        approval = next((x for x in data["approvals"] if x.get("id") == str(approval_id)), None)
        if not approval:
            raise KeyError(approval_id)
        if approval.get("status") != "pending":
            raise ValueError("approval already resolved")
        approval["status"] = "approved" if approved else "rejected"
        approval["actor"] = str(actor)
        approval["resolved_at"] = _now()
        work = next((x for x in data["work_items"] if x.get("id") == approval["work_id"]), None)
        if work:
            work["status"] = "ready" if approved else "blocked"
            work["updated_at"] = _now()
        self._audit(data, {"kind": "approval_resolved", "approval_id": approval["id"], "approved": bool(approved), "actor": str(actor)})
        self._write(data)
        return dict(approval)
