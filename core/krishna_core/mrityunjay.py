from __future__ import annotations

from pathlib import Path
from queue import Empty, Queue
from threading import Event, RLock, Thread
from typing import Any, Callable
import json
import time


class MrityunjaySelfHealBot:
    """Permanent KRISHNA self-heal supervisor.

    Mrityunjay does not replace KRISHNA's repair engine. It listens for objective
    failure signals, invokes the canonical self_heal.run action, and may
    automatically apply only a small reversible low-risk verified candidate.
    Promotion still goes through the existing transactional backup, post-apply
    verification and rollback path.

    Security/control-plane, dependency, workflow, mobile, deployment and secret
    changes are never auto-applied. They may be diagnosed and staged, but remain
    quarantined for explicit review.
    """

    VERSION = "mrityunjay-self-heal-v1"
    FAILURE_TOPICS = (
        "TEST_FAILED",
        "BUILD_FAILED",
        "VERIFICATION_FAILED",
        "MISSION_FAILED",
        "AGENT_FAILED",
        "TOOL_ERROR",
    )
    SAFE_EXACT = frozenset({
        "core/web_validation.html",
        "core/design_studio.html",
        "core/visual_editor.html",
    })
    SAFE_PREFIXES = (
        "core/krishna_core/",
        "core/tests/",
        "tests/",
    )
    SAFE_SUFFIXES = (".py", ".html", ".htm", ".css", ".scss", ".js", ".jsx", ".ts", ".tsx", ".json")
    CONTROL_PLANE_BLOCKLIST = frozenset({
        "core/krishna_core/orchestrator.py",
        "core/krishna_core/server.py",
        "core/krishna_core/shared_action_bus.py",
        "core/krishna_core/permission_runtime.py",
        "core/krishna_core/policy_kernel.py",
        "core/krishna_core/promotion_manager.py",
        "core/krishna_core/self_heal.py",
        "core/krishna_core/mrityunjay.py",
        "core/krishna_core/secure_vault.py",
        "core/krishna_core/remote_access.py",
    })
    BLOCKED_PREFIXES = (
        ".github/",
        "scripts/",
        "mobile_v3/",
        "app/spatial-ui/",
        "core/requirements/",
    )
    MAX_AUTO_FILES = 6

    def __init__(
        self,
        state_root: str | Path,
        dispatcher: Callable[..., dict],
        projects,
        event_bus=None,
        default_frontend_url: str | None = None,
        cooldown_seconds: int = 300,
        development=None,
        source_root: str | Path | None = None,
        canonical_branch: str = "fix/krishna-ui-runtime-verification",
    ):
        self.root = Path(state_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_file = self.root / "state.json"
        self.dispatcher = dispatcher
        self.projects = projects
        self.event_bus = event_bus
        self.default_frontend_url = str(default_frontend_url or "").strip() or None
        self.cooldown_seconds = max(60, int(cooldown_seconds or 300))
        self.development = development
        self.source_root = Path(source_root).resolve() if source_root else None
        self.canonical_branch = str(canonical_branch or "").strip()
        self.handoff_file = self.root / "deploy-handoff.json"
        self._restart_callback: Callable[[dict[str, Any]], dict[str, Any]] | None = None
        self._queue: Queue[dict[str, Any]] = Queue(maxsize=100)
        self._stop = Event()
        self._thread: Thread | None = None
        self._lock = RLock()
        self._last_started_by_project: dict[str, float] = {}
        self._state = self._load()
        if self.event_bus is not None:
            for topic in self.FAILURE_TOPICS:
                self.event_bus.subscribe(topic, self._on_failure_event)

    def _load(self) -> dict[str, Any]:
        if not self.state_file.is_file():
            return {
                "version": self.VERSION,
                "runs": 0,
                "healed": 0,
                "rolled_back": 0,
                "quarantined": 0,
                "last_result": None,
            }
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {
                "version": self.VERSION,
                "runs": 0,
                "healed": 0,
                "rolled_back": 0,
                "quarantined": 0,
                "last_result": {"status": "state_recovered", "reason": "state file unreadable"},
            }

    def _save(self) -> None:
        payload = dict(self._state)
        payload["version"] = self.VERSION
        tmp = self.state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        tmp.replace(self.state_file)

    @staticmethod
    def _event_project(event: dict[str, Any]) -> str:
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        project = str(payload.get("project") or "").strip()
        if project and project.lower() != "system":
            return project
        nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
        project = str(nested.get("project") or "").strip()
        return project or "KRISHNA"

    def _on_failure_event(self, event: dict[str, Any]):
        source = str(event.get("source") or "").lower()
        if "mrityunjay" in source:
            return None
        project = self._event_project(event)
        policy = self.projects.get(project)
        if not policy or getattr(policy, "role", "") != "active":
            return None
        reason = f"{event.get('topic')}: {json.dumps(event.get('payload') or {}, ensure_ascii=False, default=str)[:2000]}"
        return self.trigger(project, reason=reason, evidence={"event_id": event.get("event_id"), "topic": event.get("topic")})

    @classmethod
    def auto_apply_eligibility(cls, diff: dict[str, Any] | None) -> dict[str, Any]:
        diff = dict(diff or {})
        files = list(diff.get("added") or []) + list(diff.get("changed") or []) + list(diff.get("removed") or [])
        normalized = [str(x or "").replace("\\", "/").strip("/") for x in files]
        reasons = []
        if not normalized:
            reasons.append("no changed files")
        if len(normalized) > cls.MAX_AUTO_FILES:
            reasons.append(f"file_count exceeds {cls.MAX_AUTO_FILES}")
        if diff.get("added"):
            reasons.append("automatic new file creation is forbidden")
        if diff.get("removed"):
            reasons.append("automatic deletion is forbidden")
        for path in normalized:
            low = path.lower()
            if low in cls.CONTROL_PLANE_BLOCKLIST:
                reasons.append(f"control-plane file blocked: {path}")
                continue
            if any(low.startswith(prefix) for prefix in cls.BLOCKED_PREFIXES):
                reasons.append(f"high-risk path blocked: {path}")
                continue
            if not (low in cls.SAFE_EXACT or low.startswith(cls.SAFE_PREFIXES)):
                reasons.append(f"path outside autonomous repair scope: {path}")
                continue
            if not low.endswith(cls.SAFE_SUFFIXES):
                reasons.append(f"file type outside autonomous repair scope: {path}")
        return {
            "eligible": not reasons,
            "files": normalized,
            "reasons": reasons,
            "policy": "verified low-risk edits to existing source files only; no add/delete/control-plane/dependency/deployment/mobile auto-apply",
        }

    def bind_restart(self, callback: Callable[[dict[str, Any]], dict[str, Any]] | None):
        self._restart_callback = callback
        return {"bound": callable(callback)}

    def _write_handoff(self, payload: dict[str, Any]) -> None:
        tmp = self.handoff_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        tmp.replace(self.handoff_file)

    def _krishna_source_ready(self) -> dict[str, Any]:
        if self.development is None or self.source_root is None:
            return {"ok": False, "reason": "KRISHNA Git/development handoff is not configured"}
        snap = self.development.git_snapshot(self.source_root)
        if not snap.get("ok"):
            return {"ok": False, "reason": "KRISHNA source Git snapshot failed", "snapshot": snap}
        if not snap.get("clean"):
            return {"ok": False, "reason": "KRISHNA source working tree is not clean", "snapshot": snap}
        if self.canonical_branch and snap.get("branch") != self.canonical_branch:
            return {
                "ok": False,
                "reason": "KRISHNA source is not on the canonical branch",
                "snapshot": snap,
                "canonical_branch": self.canonical_branch,
            }
        if not callable(self._restart_callback):
            return {"ok": False, "reason": "Guardian restart handoff is not bound", "snapshot": snap}
        return {"ok": True, "snapshot": snap}

    def _rollback_source_head(self, previous_head: str, expected_current_head: str | None = None) -> dict[str, Any]:
        if self.development is None or self.source_root is None:
            return {"ok": False, "reason": "development/source root unavailable"}
        return self.development.reset_verified_head(
            self.source_root,
            previous_head,
            expected_current_head=expected_current_head,
        )

    def _upgrade_krishna(
        self,
        *,
        token: str,
        checks: list[str],
        eligibility: dict[str, Any],
        base: dict[str, Any],
    ) -> dict[str, Any]:
        ready = self._krishna_source_ready()
        if not ready.get("ok"):
            return self._record({
                **base,
                "status": "quarantined",
                "reason": ready.get("reason"),
                "auto_apply": eligibility,
                "live_project_modified": False,
            })

        before = dict(ready["snapshot"])
        previous_head = str(before.get("head") or "").strip()
        apply_receipt = self.dispatcher(
            "self_heal.apply",
            {
                "promotion_token": token,
                # The candidate already passed frontend verification against its
                # isolated preview. Do not falsely verify new source against the
                # still-old live 8766 runtime before Guardian redeploys it.
                "frontend_url": None,
                "checks": checks,
                "autonomous_policy": {
                    "name": self.VERSION,
                    "scope": "verified low-risk KRISHNA source upgrade",
                    "eligibility": eligibility,
                },
            },
            project="KRISHNA",
            source="system",
            actor="mrityunjay",
            approved=True,
            permissions=("live.write", "tests.run", "browser.test"),
            idempotency_key="mrityunjay-source-apply:" + token,
        )
        applied = dict(apply_receipt.get("result") or {})
        if not applied.get("verified"):
            return self._record({
                **base,
                "status": "rolled_back" if applied.get("rolled_back") else "apply_failed",
                "verified": False,
                "rolled_back": bool(applied.get("rolled_back")),
                "auto_apply": eligibility,
                "promotion": applied.get("promotion"),
                "post_apply_verification": applied.get("post_apply_verification"),
            })

        files = list(eligibility.get("files") or [])
        commit = self.development.commit_local(
            self.source_root,
            "MRITYUNJAY: verified autonomous self-heal",
            files,
        )
        if not commit.get("ok"):
            rollback = self._rollback_source_head(previous_head, expected_current_head=previous_head)
            return self._record({
                **base,
                "status": "rolled_back",
                "verified": False,
                "rolled_back": True,
                "reason": "verified source promotion could not be committed cleanly",
                "git_commit": commit,
                "git_rollback": rollback,
                "auto_apply": eligibility,
            })

        after = dict(commit.get("snapshot") or {})
        new_head = str(after.get("head") or "").strip()
        if not new_head or new_head == previous_head or not after.get("clean"):
            rollback = self._rollback_source_head(previous_head, expected_current_head=new_head or None)
            return self._record({
                **base,
                "status": "rolled_back",
                "verified": False,
                "rolled_back": True,
                "reason": "autonomous commit did not produce a clean new HEAD",
                "git_commit": commit,
                "git_rollback": rollback,
                "auto_apply": eligibility,
            })

        handoff = {
            "schema": 1,
            "owner": "MRITYUNJAY",
            "status": "restart_requested",
            "project": "KRISHNA",
            "branch": str(after.get("branch") or before.get("branch") or ""),
            "previous_commit": previous_head,
            "new_commit": new_head,
            "files": files,
            "created_at": time.time(),
            "policy": "deploy and runtime acceptance must pass before remote push; otherwise reset to previous commit",
        }
        try:
            self._write_handoff(handoff)
            restart = self._restart_callback(dict(handoff))
            if not (restart or {}).get("scheduled"):
                raise RuntimeError("Guardian restart handoff was not scheduled")
        except Exception as exc:
            rollback = self._rollback_source_head(previous_head, expected_current_head=new_head)
            try:
                if self.handoff_file.exists():
                    self.handoff_file.unlink()
            except OSError:
                pass
            return self._record({
                **base,
                "status": "rolled_back",
                "verified": False,
                "rolled_back": True,
                "reason": f"restart handoff failed: {type(exc).__name__}: {exc}",
                "git_rollback": rollback,
                "auto_apply": eligibility,
            })

        return self._record({
            **base,
            "status": "upgrade_restart_scheduled",
            "verified": True,
            "rolled_back": False,
            "source_committed": True,
            "source_previous_commit": previous_head,
            "source_new_commit": new_head,
            "runtime_restart_scheduled": True,
            "live_project_modified": False,
            "auto_apply": eligibility,
            "handoff": str(self.handoff_file),
        })

    def trigger(
        self,
        project: str = "KRISHNA",
        *,
        reason: str = "runtime failure signal",
        evidence: dict[str, Any] | None = None,
        frontend_url: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        project = str(project or "KRISHNA").strip() or "KRISHNA"
        item = {
            "project": project,
            "reason": str(reason or "runtime failure signal")[:4000],
            "evidence": dict(evidence or {}),
            "frontend_url": str(frontend_url or self.default_frontend_url or "").strip() or None,
            "force": bool(force),
            "queued_at": time.time(),
        }
        try:
            self._queue.put_nowait(item)
            return {"queued": True, "project": project, "queue_depth": self._queue.qsize()}
        except Exception:
            return {"queued": False, "project": project, "reason": "Mrityunjay queue is full"}

    def start(self) -> dict[str, Any]:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return self.status()
            self._stop.clear()
            self._thread = Thread(target=self._loop, name="krishna-mrityunjay", daemon=True)
            self._thread.start()
        return self.status()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=3)
        return self.status()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                item = self._queue.get(timeout=1)
            except Empty:
                continue
            try:
                self.heal_now(**item)
            finally:
                self._queue.task_done()

    def heal_now(
        self,
        project: str = "KRISHNA",
        *,
        reason: str = "manual Mrityunjay audit",
        evidence: dict[str, Any] | None = None,
        frontend_url: str | None = None,
        force: bool = False,
        queued_at: float | None = None,
    ) -> dict[str, Any]:
        project = str(project or "KRISHNA").strip() or "KRISHNA"
        policy = self.projects.get(project)
        if not policy:
            return self._record({
                "status": "blocked",
                "project": project,
                "reason": "project not registered",
                "live_project_modified": False,
            })
        if getattr(policy, "role", "") != "active":
            return self._record({
                "status": "blocked",
                "project": project,
                "reason": f"{policy.role} project is read-only",
                "live_project_modified": False,
            })

        now = time.time()
        with self._lock:
            last = float(self._last_started_by_project.get(project) or 0)
            if not force and now - last < self.cooldown_seconds:
                return self._record({
                    "status": "cooldown",
                    "project": project,
                    "reason": "duplicate failure signal suppressed",
                    "retry_after_seconds": int(self.cooldown_seconds - (now - last)),
                    "live_project_modified": False,
                })
            self._last_started_by_project[project] = now

        checks = list(getattr(policy, "verification_checks", None) or [])
        if not checks and project == "KRISHNA":
            checks = ["python-tests"]
        if not checks:
            return self._record({
                "status": "blocked",
                "project": project,
                "reason": "no registered deterministic verification checks",
                "live_project_modified": False,
            })

        url = str(frontend_url or (self.default_frontend_url if project == "KRISHNA" else "") or "").strip() or None
        run_receipt = self.dispatcher(
            "self_heal.run",
            {
                "project": project,
                "frontend_url": url,
                "checks": checks,
                "components": ["backend", "frontend", "runtime", "api", "ui"],
                "max_rounds": 2,
                "trigger": {
                    "actor": "Mrityunjay",
                    "reason": str(reason or "")[:4000],
                    "evidence": dict(evidence or {}),
                },
            },
            project=project,
            source="system",
            actor="mrityunjay",
            approved=False,
            permissions=("candidate.write", "tests.run", "browser.test", "model.use"),
        )
        result = dict(run_receipt.get("result") or {})
        base = {
            "project": project,
            "trigger_reason": str(reason or "")[:4000],
            "self_heal_status": result.get("status"),
            "self_heal_phase": result.get("phase"),
            "self_heal_verified": bool(result.get("verified")),
            "live_project_modified": False,
            "queued_at": queued_at,
        }

        if result.get("status") == "healthy":
            return self._record({**base, "status": "healthy"})

        promotion = result.get("promotion") if isinstance(result.get("promotion"), dict) else {}
        token = str(promotion.get("promotion_token") or "").strip()
        if not (result.get("verified") and token):
            return self._record({
                **base,
                "status": "diagnosed_not_applied",
                "error": result.get("error"),
                "repair_rounds": len(result.get("repair_rounds") or []),
            })

        eligibility = self.auto_apply_eligibility(promotion.get("diff"))
        if not eligibility["eligible"]:
            return self._record({
                **base,
                "status": "quarantined",
                "promotion_token": token,
                "auto_apply": eligibility,
                "candidate_root": result.get("candidate_root"),
            })

        if project == "KRISHNA":
            return self._upgrade_krishna(
                token=token,
                checks=checks,
                eligibility=eligibility,
                base=base,
            )

        apply_receipt = self.dispatcher(
            "self_heal.apply",
            {
                "promotion_token": token,
                "frontend_url": url,
                "checks": checks,
                "axe_required": True,
                "performance_required": True,
                "autonomous_policy": {
                    "name": self.VERSION,
                    "scope": "low-risk verified reversible repair",
                    "eligibility": eligibility,
                },
            },
            project=project,
            source="system",
            actor="mrityunjay",
            approved=True,
            permissions=("live.write", "tests.run", "browser.test"),
            idempotency_key="mrityunjay-apply:" + token,
        )
        applied = dict(apply_receipt.get("result") or {})
        verified = bool(applied.get("verified"))
        rolled_back = bool(applied.get("rolled_back"))
        return self._record({
            **base,
            "status": "healed" if verified else "rolled_back" if rolled_back else "apply_failed",
            "verified": verified,
            "rolled_back": rolled_back,
            "live_project_modified": verified,
            "auto_apply": eligibility,
            "promotion": applied.get("promotion"),
            "post_apply_verification": applied.get("post_apply_verification"),
        })

    def _record(self, result: dict[str, Any]) -> dict[str, Any]:
        row = dict(result)
        row["completed_at"] = time.time()
        with self._lock:
            self._state["runs"] = int(self._state.get("runs") or 0) + 1
            if row.get("status") == "healed":
                self._state["healed"] = int(self._state.get("healed") or 0) + 1
            if row.get("rolled_back") or row.get("status") == "rolled_back":
                self._state["rolled_back"] = int(self._state.get("rolled_back") or 0) + 1
            if row.get("status") == "quarantined":
                self._state["quarantined"] = int(self._state.get("quarantined") or 0) + 1
            self._state["last_result"] = row
            self._save()
        return row

    def status(self) -> dict[str, Any]:
        thread = self._thread
        with self._lock:
            return {
                "name": "MRITYUNJAY",
                "version": self.VERSION,
                "role": "permanent KRISHNA self-heal supervisor",
                "running": bool(thread and thread.is_alive()),
                "queue_depth": self._queue.qsize(),
                "cooldown_seconds": self.cooldown_seconds,
                "failure_topics": list(self.FAILURE_TOPICS),
                "automatic_low_risk_apply": True,
                "automatic_krishna_upgrade": bool(self.development is not None and self.source_root is not None and callable(self._restart_callback)),
                "transactional_rollback_required": True,
                "deployment_handoff": str(self.handoff_file),
                "human_intervention": "not required for eligible low-risk verified repairs; KRISHNA source upgrades use clean Git + Guardian verified deploy handoff; high-risk/control-plane/dependency/deployment/mobile changes remain quarantined",
                "state": dict(self._state),
            }
