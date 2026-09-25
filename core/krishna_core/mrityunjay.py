from __future__ import annotations

from pathlib import Path
import json
import os
import threading
import time


class MrityunjayRuntime:
    """Event-driven, bounded KRISHNA self-heal supervisor.

    Mrityunjay never edits live files directly. It asks the canonical self-heal
    pipeline to diagnose, repair in an isolated candidate, verify, promote, and
    rollback on failed post-apply verification. Automatic healing is enabled only
    when KRISHNA_ALLOW_ACTIONS is enabled and the event is not produced by a
    self-heal/promotion loop.
    """

    VERSION = "mrityunjay-v1"
    TRIGGERS = ("action.failed", "TEST_FAILED", "BUILD_FAILED", "VERIFICATION_FAILED")
    IGNORED_ACTION_PREFIXES = ("mrityunjay.", "self_heal.", "promotion.")
    DEFAULT_COOLDOWN_SECONDS = 900

    def __init__(self, state_root: str | Path, event_bus, memory=None, *,
                 enabled: bool | None = None, cooldown_seconds: int | None = None):
        self.root = Path(state_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.event_bus = event_bus
        self.memory = memory
        if enabled is None:
            enabled = str(os.getenv("KRISHNA_ALLOW_ACTIONS", "0")).strip().lower() in {"1", "true", "yes", "on"}
        self.enabled = bool(enabled)
        self.cooldown_seconds = max(60, int(cooldown_seconds or self.DEFAULT_COOLDOWN_SECONDS))
        self._heal = None
        self._attached = False
        self._lock = threading.RLock()
        self._busy = False
        self._last_by_project: dict[str, float] = {}
        self.last_result = None
        self.last_trigger = None
        self.run_count = 0
        self.trigger_count = 0

    def bind(self, heal_callable):
        if not callable(heal_callable):
            raise TypeError("Mrityunjay heal callback must be callable")
        self._heal = heal_callable
        return self.status()

    def attach(self):
        if self._attached:
            return self.status()
        for topic in self.TRIGGERS:
            self.event_bus.subscribe(topic, self._on_event)
        self._attached = True
        return self.status()

    def detach(self):
        if not self._attached:
            return self.status()
        for topic in self.TRIGGERS:
            self.event_bus.unsubscribe(topic, self._on_event)
        self._attached = False
        return self.status()

    @staticmethod
    def _payload(event):
        payload = event.get("payload") if isinstance(event, dict) else {}
        return payload if isinstance(payload, dict) else {}

    def _event_project(self, event):
        payload = self._payload(event)
        return str(payload.get("project") or "KRISHNA").strip() or "KRISHNA"

    def _ignored(self, event):
        payload = self._payload(event)
        action = str(payload.get("action") or "")
        actor = str(payload.get("actor") or "")
        if actor == "mrityunjay":
            return True
        return any(action.startswith(prefix) for prefix in self.IGNORED_ACTION_PREFIXES)

    def _cooldown_ready(self, project, now=None):
        now = float(now or time.time())
        return now - float(self._last_by_project.get(project) or 0) >= self.cooldown_seconds

    def _record(self, status, detail):
        if not self.memory:
            return
        try:
            self.memory.audit("mrityunjay", status, str(detail)[:12000])
        except Exception:
            pass

    def _run_thread(self, project, reason, evidence):
        try:
            result = self.run_now(project=project, reason=reason, evidence=evidence)
            self.last_result = result
        except Exception as exc:
            self.last_result = {
                "ok": False,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
                "project": project,
            }
            self._record("error", self.last_result)
        finally:
            with self._lock:
                self._busy = False

    def _on_event(self, event):
        self.trigger_count += 1
        self.last_trigger = {
            "topic": str((event or {}).get("topic") or ""),
            "project": self._event_project(event or {}),
            "created_at": (event or {}).get("created_at"),
        }
        if not self.enabled or not self._heal or self._ignored(event or {}):
            return {"scheduled": False, "reason": "disabled_or_ignored"}
        project = self._event_project(event or {})
        now = time.time()
        with self._lock:
            if self._busy:
                return {"scheduled": False, "reason": "busy"}
            if not self._cooldown_ready(project, now):
                return {"scheduled": False, "reason": "cooldown"}
            self._busy = True
            self._last_by_project[project] = now
        payload = self._payload(event or {})
        reason = f"{(event or {}).get('topic')}: {payload.get('action') or payload.get('reason') or payload.get('error') or 'runtime failure'}"
        thread = threading.Thread(
            target=self._run_thread,
            args=(project, reason, {"event": event}),
            name=f"mrityunjay-heal-{project}",
            daemon=True,
        )
        thread.start()
        return {"scheduled": True, "project": project, "reason": reason}

    def run_now(self, *, project="KRISHNA", reason="manual audit", evidence=None, **kwargs):
        if not self._heal:
            raise RuntimeError("Mrityunjay heal callback is not bound")
        started = time.time()
        self.run_count += 1
        result = self._heal(
            project=str(project or "KRISHNA"),
            reason=str(reason or "manual audit"),
            evidence=dict(evidence or {}),
            **kwargs,
        )
        wrapped = {
            "ok": bool(result.get("verified") or result.get("status") == "healthy"),
            "project": str(project or "KRISHNA"),
            "reason": str(reason or "manual audit"),
            "elapsed_seconds": round(time.time() - started, 3),
            "result": result,
        }
        self.last_result = wrapped
        self._record("completed" if wrapped["ok"] else "incomplete", wrapped)
        return wrapped

    def status(self):
        return {
            "name": "MRITYUNJAY",
            "version": self.VERSION,
            "role": "internal autonomous self-heal and recovery supervisor",
            "enabled": self.enabled,
            "attached": self._attached,
            "bound": bool(self._heal),
            "busy": self._busy,
            "triggers": list(self.TRIGGERS),
            "cooldown_seconds": self.cooldown_seconds,
            "run_count": self.run_count,
            "trigger_count": self.trigger_count,
            "last_trigger": self.last_trigger,
            "last_result": self.last_result,
            "automatic_scope": "bounded reversible source repair only after deterministic verification",
            "blocked_scope": [
                "credentials/secrets",
                "dependency manifests",
                "CI/workflows",
                "security-policy bypass",
                "external side effects",
                "hardware control",
            ],
            "promotion_rule": "transactional promotion + post-apply verification + rollback",
        }
