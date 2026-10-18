"""Canonical, permission-gated bridge from SUDARSHAN research to KRISHNA.

Uses KRISHNA's existing Shared Action Bus, project bootstrap, Gyan-Bhandar
approval queue and BRAHMAGYAN research missions. This module creates no new
identity, permission, memory, worktree or orchestration subsystem.

REA/MiroFish results are *observations*, not verified product facts.
"""
from pathlib import Path
from collections.abc import Mapping
import re

ENGINES = frozenset(("REA", "MiroFish"))
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_ACTION_OBSERVE = "sudarshan.research.observe"
_ACTION_MISSION = "sudarshan.research.mission"


class SudarshanCanonicalIntegration:
    """Registered actions are the *only* entry points for this bridge."""

    def __init__(self, projects, gyan_bhandar, brahmagyan, runner=None, *,
                 rea_executable=None, mirofish_base_url="http://127.0.0.1:5001",
                 consent=None, evidence_root=None):
        self.rea_executable = rea_executable
        self.mirofish_base_url = mirofish_base_url
        self.consent = consent
        self.evidence_root = Path(evidence_root).resolve() if evidence_root is not None else None
        self.projects = projects
        self.gyan = gyan_bhandar
        self.brahmagyan = brahmagyan
        if runner is not None and not callable(runner):
            raise TypeError("runner must be callable")
        self.runner = runner

    @staticmethod
    def _project(payload, context):
        if not isinstance(payload, Mapping):
            raise TypeError("research payload must be an object")
        project = payload.get("project_id")
        if not isinstance(project, str) or not project.strip():
            raise ValueError("project_id required")
        if project != context.get("project"):
            raise PermissionError("research project must equal authorized action scope")
        return project

    def _engine_spec(self, engine, spec, project, project_context):
        if engine not in ENGINES:
            raise ValueError("unsupported research engine")
        if not isinstance(spec, dict):
            raise TypeError("adapter spec must be an object")
        if "evidence_root" in spec:
            raise PermissionError("only KRISHNA supervisor may choose evidence storage")
        if engine == "MiroFish":
            if spec.get("project_id") != project:
                raise PermissionError("MiroFish simulation project mismatch")
            if spec.get("base_url", "http://127.0.0.1:5001") != self.mirofish_base_url:
                raise PermissionError("MiroFish API endpoint must match supervisor configuration")
            if not isinstance(spec.get("simulation_id"), str) or not spec["simulation_id"].strip():
                raise ValueError("simulation_id required")
        else:
            repository = project_context.get("repository")
            if not isinstance(repository, str) or not repository.strip():
                raise ValueError("local project repository required for REA")
            if not isinstance(spec.get("root"), str) or not isinstance(spec.get("target"), str):
                raise ValueError("REA requires target and local root")
            if not Path(repository).is_absolute() or not Path(spec["root"]).is_absolute():
                raise ValueError("REA root and project repository must be absolute local paths")
            if Path(repository).resolve() != Path(spec["root"]).resolve():
                raise PermissionError("REA root must match the authorized project repository")
            if not self.rea_executable:
                raise RuntimeError("REA must be explicitly configured on KRISHNA supervisor")
            if spec.get("rea_executable") != self.rea_executable:
                raise PermissionError("REA executable must match supervisor-allowlisted executable")

    def _dispatch(self, engine, spec, project):
        # Never interpret a shell string or invoke arbitrary executables here.
        # The existing allowlisted tool adapters implement their own validation.
        if self.runner is not None:
            return self.runner(engine, spec, authorized=True)
        if self.evidence_root is None:
            raise RuntimeError("canonical evidence root not configured")
        try:
            from tools.sudarshan_native_cli import dispatch
            from tools.sudarshan_evidence_archive import verify
        except ImportError as error:
            raise RuntimeError("SUDARSHAN tool adapters unavailable on this runtime host") from error
        local_spec = dict(spec)
        local_spec["project_id"] = project
        local_spec["evidence_root"] = str(self.evidence_root)
        result = dispatch(engine, local_spec, authorized=True)
        if getattr(result, "status", None) == "passed" and not verify(
                self.evidence_root, project, engine, result.evidence_id):
            raise RuntimeError("adapter digest has no locally verified raw evidence")
        return result

    def _require_consent(self, payload, action_context, action, project):
        if (self.consent is None or not action_context.get("approved") or
                action_context.get("source") != "pc" or
                action_context.get("action") != action):
            raise PermissionError("local operator consent is not configured")
        if not isinstance(payload.get("owner_token"), str):
            raise PermissionError("SUDARSHAN owner_token required")
        self.consent.consume(payload["owner_token"], action, project, payload)

    def observe(self, payload, action_context):
        project = self._project(payload, action_context)
        self._require_consent(payload, action_context, _ACTION_OBSERVE, project)
        project_context = payload.get("project_context")
        if not isinstance(project_context, dict):
            raise ValueError("canonical project bootstrap context required")
        lifecycle = self.projects.start(project, project_context)
        if lifecycle.get("state") != "DISCOVERY":
            raise PermissionError("project bootstrap incomplete; observation blocked")
        engine = payload.get("engine")
        spec = payload.get("spec")
        self._engine_spec(engine, spec, project, project_context)
        topic = payload.get("topic")
        if not isinstance(topic, str) or not topic.strip() or len(topic) > 200:
            raise ValueError("bounded research topic required")
        result = self._dispatch(engine, spec, project)
        if (getattr(result, "engine", None) != engine or
                getattr(result, "status", None) != "passed"):
            raise RuntimeError("research adapter did not provide a successful observation")
        evidence_id = getattr(result, "evidence_id", None)
        if not isinstance(evidence_id, str) or not _DIGEST.fullmatch(evidence_id):
            raise ValueError("research evidence digest missing or malformed")
        summary = getattr(result, "summary", None)
        if not isinstance(summary, str) or not summary.strip() or len(summary) > 2000:
            raise ValueError("research observation summary invalid")

        # Reuse the canonical Gyan approval queue: no automatic knowledge trust.
        proposed = self.gyan.propose(
            project, topic.strip(), summary,
            evidence=[{"source": engine, "evidence_id": evidence_id, "project": project}],
            confidence=0.0, source="sudarshan:" + engine,
            verified=False, memory_kind="evidence",
            provenance={"engine": engine, "evidence_id": evidence_id,
                        "status": "unverified_observation", "project": project},
        )
        if not proposed.get("approval_id") or proposed.get("stored") is not False:
            raise RuntimeError("canonical knowledge proposal was not queued")
        return {
            "state": "PENDING_GYAN_APPROVAL",
            "project": project, "engine": engine,
            "evidence_id": evidence_id,
            "approval_id": proposed["approval_id"],
            "research_mission_created": False,
            "requires_user_approval": True,
            "release_ready": False,
            "verification": {
                "passed": True,
                "reason": "adapter execution and pending-queue handoff verified; "
                          "observation content and product behavior NOT verified",
            },
        }

    def mission(self, payload, action_context):
        project = self._project(payload, action_context)
        self._require_consent(payload, action_context, _ACTION_MISSION, project)
        proposal_id = payload.get("approval_id")
        if not isinstance(proposal_id, str) or not proposal_id.strip():
            raise ValueError("approval_id required")
        candidate = self.gyan.memory.gyan_pending(proposal_id)
        if (not isinstance(candidate, dict) or candidate.get("project") != project or
                candidate.get("status") != "pending" or
                candidate.get("source") not in {"sudarshan:REA", "sudarshan:MiroFish"} or
                candidate.get("verified") is not False):
            raise PermissionError("no matching pending, unverified research evidence")
        refs = candidate.get("evidence")
        if (not isinstance(refs, list) or not refs or
                any(not isinstance(row, dict) or
                    row.get("project") != project or
                    not isinstance(row.get("evidence_id"), str) or
                    not _DIGEST.fullmatch(row["evidence_id"]) for row in refs)):
            raise ValueError("research source evidence is untraceable")

        topic = candidate.get("topic")
        if not isinstance(topic, str) or not topic.strip():
            raise ValueError("research topic missing")
        mission = self.brahmagyan.create_mission(
            project, topic, question="Verify untrusted research evidence for " + topic,
            knowledge_track="engineering", target_level="L3",
        )
        if not isinstance(mission, dict) or not mission.get("mission_id"):
            raise RuntimeError("canonical BRAHMAGYAN mission not created")
        return {
            "state": "RESEARCH_PLANNED",
            "mission_id": mission["mission_id"],
            "project": project,
            "source_approval_id": proposal_id,
            "evidence_ids": [row["evidence_id"] for row in refs],
            "claim_verified": False,
            "gyan_promoted": False,
            "release_ready": False,
            "verification": {
                "passed": True,
                "reason": "canonical research mission created; facts await research and review",
            },
        }

    def register(self, bus):
        observe = bus.register(
            _ACTION_OBSERVE, self.observe,
            description="Collect scoped REA/MiroFish evidence into canonical Gyan review",
            mutating=True, requires_approval=True,
            permissions=("research.inspect", "memory.write"),
            sources=("pc",),
        )
        mission = bus.register(
            _ACTION_MISSION, self.mission,
            description="Create BRAHMAGYAN verification mission from pending research evidence",
            mutating=True, requires_approval=True,
            permissions=("research.inspect", "memory.write"),
            sources=("pc",),
        )
        return {"observe": observe, "mission": mission}
