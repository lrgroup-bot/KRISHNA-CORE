"""Hybrid implementation policy: cloud research produces evidence; local agents build.

This module deliberately does not call a cloud provider or execute code. It supplies
an auditable plan that a registered KRISHNA workflow can execute using existing
GARUDA search, BRAHMAGYAN review and SUDARSHAN local workers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HybridStage:
    name: str
    execution: str
    purpose: str
    approval_required: bool = False


STAGES = (
    HybridStage("public_research", "cloud_free_verified", "Search public documentation and repositories; collect dated source links."),
    HybridStage("evidence_review", "local", "Treat all retrieved content as untrusted; verify licenses, relevance and technical claims."),
    HybridStage("implementation_plan", "local", "Compare findings with local project state; select bounded changes."),
    HybridStage("isolated_build", "local", "Use registered workers in a disposable worktree; do not run retrieved shell instructions."),
    HybridStage("test_and_review", "local", "Run unit, integration, security and rollback checks."),
    HybridStage("learn", "local", "Record evidence, changes and verified outcomes without storing secrets."),
)


def hybrid_implementation_plan(*, task: str, project: str, approved_public_context: bool = False) -> dict[str, Any]:
    """Return an execution contract, never an authorization to upload code."""
    if not isinstance(task, str) or not task.strip():
        raise ValueError("task must be non-empty")
    if not isinstance(project, str) or not project.strip():
        raise ValueError("project must be non-empty")
    return {
        "policy": "cloud_research_local_build",
        "task": task.strip(),
        "project": project.strip(),
        "cloud_allowed": bool(approved_public_context),
        "cloud_policy": {
            "strict_zero_credit": True,
            "no_paid_fallback": True,
            "only_public_or_explicitly_approved_context": True,
            "no_secrets_or_private_repo_upload": True,
            "source_citations_required": True,
            "cloud_failure_behavior": "continue_local_with_existing_evidence_or_report_blocked",
        },
        "local_policy": {
            "registered_workers_only": True,
            "isolated_workspace": True,
            "tests_before_merge": True,
            "human_approval_for_sensitive_mutations": True,
        },
        "stages": [vars(stage) for stage in STAGES],
    }


def execute_hybrid_implementation(
    *, task: str, project: str, approved_public_context: bool,
    research, local_plan, local_build, local_test, local_learn,
    approve_build=False,
):
    """Run an injected, policy-gated hybrid workflow.

    Research receives only the public task string, never repository contents.
    Callbacks are registered trusted adapters supplied by the host; this function
    neither executes arbitrary model output nor grants filesystem permissions.
    """
    import os
    from urllib.parse import urlparse

    policy = hybrid_implementation_plan(
        task=task, project=project, approved_public_context=approved_public_context
    )
    if os.getenv("KRISHNA_STRICT_ZERO_CREDIT", "1").strip().lower() in {"0", "false", "no", "off"}:
        raise PermissionError("Hybrid workflow requires strict zero-credit mode")
    if not policy["cloud_allowed"]:
        return {"status": "blocked", "reason": "public_research_not_approved", "policy": policy}
    if not all(callable(fn) for fn in (research, local_plan, local_build, local_test, local_learn)):
        raise TypeError("All workflow adapters must be registered callables")

    # The host must supply a trusted research adapter which checks free-tier
    # eligibility independently. The research result is untrusted evidence.
    evidence = research(task=policy["task"], project=project, free_only=True)
    if not isinstance(evidence, dict) or evidence.get("verified_free") is not True:
        return {"status": "blocked", "reason": "cloud_free_not_verified", "policy": policy}
    sources = evidence.get("sources")
    if not isinstance(sources, list) or not sources:
        return {"status": "blocked", "reason": "missing_research_sources", "policy": policy}
    for item in sources:
        if not isinstance(item, dict) or not isinstance(item.get("url"), str):
            return {"status": "blocked", "reason": "invalid_source", "policy": policy}
        parsed = urlparse(item["url"])
        if parsed.scheme != "https" or not parsed.hostname:
            return {"status": "blocked", "reason": "non_https_source", "policy": policy}
    # Only public evidence is transferred to the local planning adapter.
    public_evidence = {"sources": [{"url": s["url"], "title": str(s.get("title", ""))[:200]} for s in sources[:20]],
                       "summary": str(evidence.get("summary", ""))[:8000]}
    plan = local_plan(task=task, project=project, evidence=public_evidence)
    if not isinstance(plan, dict):
        return {"status": "blocked", "reason": "invalid_local_plan", "policy": policy}
    if type(approve_build) is not bool:
        raise TypeError("approve_build must be a boolean")
    if not approve_build:
        return {"status": "awaiting_approval", "plan": plan, "sources": sources, "policy": policy}
    # The host must bind local_build to its registered isolated-worker boundary.
    built = local_build(project=project, plan=plan, isolated=True)
    tested = local_test(project=project, build=built)
    passed = isinstance(tested, dict) and tested.get("passed") is True
    if not passed:
        return {"status": "test_failed", "tests": tested, "sources": sources, "policy": policy}
    learned = local_learn(project=project, task=task, sources=sources, tests=tested)
    return {"status": "verified", "tests": tested, "learning": learned, "sources": sources, "policy": policy}
