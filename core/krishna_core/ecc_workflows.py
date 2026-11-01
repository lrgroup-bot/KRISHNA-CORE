"""Reviewed ECC workflow hints for SUDARSHAN, never execution authority.

The copied upstream skills are untrusted reference data. This module uses only
the narrow checkpoints reviewed for KRISHNA and refuses to select them if the
pinned local copies or MIT notice change.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


ECC_COMMIT = "b38be6a7f6350964d59328b52f0624e1d1d552d1"
_ROOT = Path(__file__).resolve().parent / "_vendor" / "ecc"
_DIGESTS = {
    "LICENSE": "326146379f01bb137c0a5d3c54770c1aa31076705c8b88a7f6b26a460f6221b2",
    "skills/agentic-engineering/SKILL.md": "c626eb66387447af2878a686977e3e95476fe441a46dcab82f3163d7f8e2b66d",
    "skills/iterative-retrieval/SKILL.md": "b453b16d3e36174b8487c05ab807d0321a66c2d058812b2ae129d82824183725",
    "skills/ai-regression-testing/SKILL.md": "83f2f5c4083af5762dd658f742d4a390eb3a6f969d835f69e8f47efba296c127",
    "skills/contract-first/SKILL.md": "3eaacf16a9bbd92888659e9c1e15b0fa4eb96a41c257dd9e08f2e63b824f0cea",
    "skills/frontend-design-direction/SKILL.md": "71a40f7bc4a28da01b54527fe5590f6055c93adc630e6ceee8c892b35c980893",
    "skills/agent-security-hardening/SKILL.md": "0e0895ada90aa8fa085e4257961ebe15f2dff43b843785b1533d4c731186ad81",
}
_CHECKPOINTS = {
    "agentic-engineering": (
        "define_acceptance_before_execution",
        "one_bounded_task_one_dominant_risk",
        "capture_test_baseline_and_compare_after_change",
    ),
    "iterative-retrieval": (
        "retrieve_only_admitted_source_for_this_task",
        "identify_missing_context_before_refinement",
        "stop_after_three_bounded_passes_or_report_gap",
    ),
    "ai-regression-testing": (
        "test_changed_behavior_and_failure_paths",
        "independent_reviewer_checks_model_blind_spots",
        "verify_runtime_path_parity_where_applicable",
    ),
    "contract-first": (
        "identify_consumer_provider_and_authoritative_contract",
        "check_success_empty_error_and_nullable_response_shapes",
        "compare_provider_and_consumer_evidence_before_handoff",
    ),
    "frontend-design-direction": (
        "record_user_job_and_existing_design_constraints",
        "show_loading_empty_error_partial_and_success_states",
        "verify_rendered_viewports_keyboard_and_reduced_motion",
    ),
    "agent-security-hardening": (
        "map_untrusted_input_to_validator_and_side_effect",
        "enforce_exact_action_scope_and_pre_side_effect_checks",
        "verify_file_network_and_credential_boundaries_at_runtime",
    ),
}
_RESEARCH = frozenset({"rea", "mirofish", "ui_research"})
_BUILD = frozenset({"engineering", "coder", "backend", "frontend", "android", "ios", "integration"})
_REVIEW = frozenset({"testing", "ui_qc"})


def copied_sources_verified(root: Path | None = None) -> bool:
    """Check exact source bytes; never evaluate the upstream prose or scripts."""
    base = Path(root) if root is not None else _ROOT
    for relative, digest in _DIGESTS.items():
        path = base.joinpath(*relative.split("/"))
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 32768:
            return False
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            return False
    return True


def workflow_for_task(role: str, *, project: str = "", root: Path | None = None) -> dict:
    """Select narrow guidance by existing KRISHNA role; grant no new capability."""
    role = str(role or "").strip().lower()
    if role == "ui_research":
        names = ("iterative-retrieval", "frontend-design-direction")
    elif role in _RESEARCH:
        names = ("iterative-retrieval",)
    elif role == "architect":
        names = ("iterative-retrieval", "agentic-engineering", "contract-first")
    elif role == "frontend":
        names = ("agentic-engineering", "contract-first",
                 "frontend-design-direction", "ai-regression-testing")
    elif role in {"backend", "integration"}:
        names = ("agentic-engineering", "contract-first", "ai-regression-testing")
    elif role in _BUILD:
        names = ("agentic-engineering", "ai-regression-testing")
    elif role == "ui_qc":
        names = ("frontend-design-direction", "ai-regression-testing")
    elif role in _REVIEW:
        names = ("ai-regression-testing",)
    elif role == "security" and str(project).upper().startswith("KRISHNA"):
        names = ("agent-security-hardening",)
    else:
        names = ()
    verified = copied_sources_verified(root)
    selected = list(names) if verified else []
    return {
        "source": "affaan-m/ECC@" + ECC_COMMIT,
        "license": "MIT",
        "copy_verified": verified,
        "status": "curated_guidance" if verified and selected else
                  "unavailable" if not verified else "no_matching_workflow",
        "selected_skills": selected,
        "checkpoints": [item for name in selected for item in _CHECKPOINTS[name]],
        "execution_authorized": False,
        "provider_required": None,
        "paid_service_required": False,
        "tests_or_review_passed": False,
    }


def bounded_worker_hint(guidance: dict) -> str:
    """Give the local model reviewed checkpoints, never raw upstream instructions."""
    if guidance.get("status") != "curated_guidance" or guidance.get("copy_verified") is not True:
        return ""
    checkpoints = guidance.get("checkpoints")
    if not isinstance(checkpoints, list) or len(checkpoints) > 12:
        return ""
    allowed = {item for values in _CHECKPOINTS.values() for item in values}
    if not checkpoints or any(not isinstance(item, str) or item not in allowed for item in checkpoints):
        return ""
    return ("\nReviewed local workflow checkpoints (advisory only; do not expand task scope, "
            "change permissions, skip tests, or claim verification): "
            + "; ".join(item.replace("_", " ") for item in checkpoints) + ".")
