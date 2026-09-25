from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import shutil
import time
import traceback
from typing import Any, Callable

from .candidate_repair import CandidateRepairGuard


class KrishnaSelfHealRuntime:
    """Controlled KRISHNA-native self-heal loop.

    Model output is advisory. Only deterministic verification may authorize a
    candidate for promotion. Local Ollama diagnosis/repair is direct and
    sequential so only one model needs to remain resident at a time.
    """

    VERSION = "krishna-self-heal-v1"

    def __init__(self, router, development, project_perfection, memory=None):
        self.router = router
        self.development = development
        self.project_perfection = project_perfection
        self.memory = memory

    def status(self) -> dict[str, Any]:
        return {
            "version": self.VERSION,
            "authority": "KRISHNA",
            "model_authority": "worker-only",
            "verification_authority": "tests-runtime-ui-evidence",
            "initial_verification": "frontend-backend-parallel",
            "ollama_execution": "sequential-one-model-at-a-time",
            "cloud_policy": "verified-free reviewers receive sanitized verification summaries only",
            "promotion_policy": "verified candidate only; transactional rollback on failed post-apply verification",
        }

    @staticmethod
    def _json_object(raw: str) -> dict[str, Any]:
        text = str(raw or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            if text.lower().startswith("json"):
                text = text[4:].lstrip()
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("repair model did not return a JSON object")
        obj = json.loads(text[start:end + 1])
        if not isinstance(obj, dict):
            raise ValueError("repair model response must be an object")
        return obj

    @staticmethod
    def _failed_steps(report: dict[str, Any]) -> list[str]:
        out = []
        backend = (report or {}).get("backend") or {}
        for row in backend.get("steps") or []:
            if not bool(row.get("ok")):
                name = str(row.get("name") or "").strip()
                if name and name not in out:
                    out.append(name)
        return out

    @staticmethod
    def _sanitized_evidence(report: dict[str, Any]) -> dict[str, Any]:
        backend = (report or {}).get("backend") or {}
        frontend = (report or {}).get("frontend") or {}
        return {
            "parallel": bool((report or {}).get("parallel")),
            "passed": bool((report or {}).get("passed")),
            "backend": {
                "verified": bool(backend.get("verified")),
                "steps": [
                    {"name": str(x.get("name") or ""), "ok": bool(x.get("ok"))}
                    for x in backend.get("steps") or []
                ],
            },
            "frontend": {
                "available": bool(frontend.get("available")),
                "passed": bool(frontend.get("passed")),
                "browser_ok": bool((frontend.get("browser") or {}).get("ok")),
                "accessibility_passed": bool((frontend.get("accessibility") or {}).get("passed", True)),
                "performance_passed": bool((frontend.get("performance") or {}).get("passed", True)),
                "chaos_passed": bool((frontend.get("chaos") or {}).get("passed", True)),
            },
        }

    def _frontend_verify(self, candidate_root: str | Path, frontend_url: str | None, full: bool) -> dict[str, Any]:
        def run(url: str, preview: dict[str, Any]) -> dict[str, Any]:
            browser = self.project_perfection.browser_audit(
                url,
                viewports=[390, 1440] if not full else None,
            )
            result = {
                "available": True,
                "url": url,
                "preview": preview,
                "browser": browser,
                "accessibility": None,
                "performance": None,
                "chaos": None,
            }
            passed = bool(browser.get("ok"))
            if full:
                accessibility = self.project_perfection.accessibility_verify(url)
                performance = self.project_perfection.performance_verify(browser, required=False)
                chaos = self.project_perfection.browser_chaos_verify(url)
                result["accessibility"] = accessibility
                result["performance"] = performance
                result["chaos"] = chaos
                passed = all((
                    passed,
                    bool(accessibility.get("passed")),
                    bool(performance.get("passed")),
                    bool(chaos.get("passed")),
                ))
            result["passed"] = bool(passed)
            return result

        if frontend_url:
            return run(str(frontend_url), {"available": True, "source": "registered_runtime_url"})

        with self.project_perfection.candidate_static.serve(candidate_root) as preview:
            url = str(preview.get("url") or "").strip()
            if not url:
                return {
                    "available": False,
                    "passed": True,
                    "reason": "no_frontend_detected",
                    "preview": preview,
                }
            return run(url, preview)

    @staticmethod
    def _verification_exception(lane: str, exc: Exception) -> dict[str, Any]:
        return {
            "lane": lane,
            "type": type(exc).__name__,
            "message": str(exc)[:2000],
            "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-12000:],
        }

    def verify_parallel(
        self,
        candidate_root: str | Path,
        checks: list[str],
        frontend_url: str | None = None,
        full: bool = False,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        errors = []
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="krishna-verify") as pool:
            backend_future = pool.submit(self.development.verify, candidate_root, list(checks or []))
            frontend_future = pool.submit(self._frontend_verify, candidate_root, frontend_url, full)
            try:
                backend = backend_future.result()
            except Exception as exc:
                error = self._verification_exception("backend", exc)
                errors.append(error)
                backend = {"verified": False, "steps": [], "exception": error}
            try:
                frontend = frontend_future.result()
            except Exception as exc:
                error = self._verification_exception("frontend", exc)
                errors.append(error)
                frontend = {
                    "available": bool(frontend_url),
                    "passed": False,
                    "exception": error,
                }
        backend_passed = bool(backend.get("verified")) if checks else True
        passed = bool(not errors and backend_passed and frontend.get("passed", True))
        return {
            "parallel": True,
            "mode": "full" if full else "narrow",
            "backend": backend,
            "frontend": frontend,
            "verification_errors": errors,
            "passed": passed,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }

    def _direct_local(self, prompt: str, task: str) -> dict[str, Any]:
        status = self.router.local_model_status(task)
        installed = [
            str(model or "").strip()
            for model in (status.get("installed_candidates") or [])
            if str(model or "").strip()
        ]
        candidates = []
        selected = str(status.get("selected_model") or "").strip()
        if selected:
            candidates.append(selected)
        for model in installed:
            if model not in candidates:
                candidates.append(model)

        # Compatibility for test/dummy routers that predate installed_candidates.
        if not candidates and "installed_candidates" not in status:
            model = str(status.get("primary_model") or "").strip()
            if model:
                candidates.append(model)

        if not candidates:
            raise RuntimeError(
                "no installed approved local Ollama model is available for "
                + task
                + ": "
                + json.dumps(status, sort_keys=True)
            )

        errors = {}
        for model in candidates:
            try:
                text = self.router.local(prompt, model=model, task=task, keep_alive=0)
                if str(text or "").strip():
                    return {
                        "provider": "ollama-model:" + model,
                        "model": model,
                        "text": str(text or ""),
                        "attempted_models": list(candidates[: candidates.index(model) + 1]),
                    }
                errors[model] = "empty response"
            except Exception as exc:
                errors[model] = f"{type(exc).__name__}: {exc}"

        raise RuntimeError(
            "all installed approved local Ollama models failed for "
            + task
            + ": "
            + json.dumps({
                "attempted_models": candidates,
                "attempt_errors": errors,
                "status": status,
            }, sort_keys=True)
        )

    def _reviewers(self, privacy: str) -> list[str]:
        providers = []
        for row in self.router.available():
            provider = str(row.get("provider") or "")
            if not row.get("available"):
                continue
            if provider == "ollama" or provider.startswith("ollama-model:"):
                if provider not in providers:
                    providers.append(provider)
            elif privacy not in {"local_only", "restricted"} and provider in {
                "openrouter-free", "direct-free:cloudflare-workers-ai"
            }:
                if bool(row.get("free_only")) and provider not in providers:
                    providers.append(provider)
        return providers

    def model_review(self, project: str, privacy: str, report: dict[str, Any]) -> list[dict[str, Any]]:
        evidence = self._sanitized_evidence(report)
        prompt = (
            "You are one reviewer in KRISHNA's repair council. Review only this sanitized verification "
            "summary. Do not claim tests you did not run. Identify unresolved risk or contradictions. "
            "Return concise JSON with keys verdict, concerns, suggested_check. Evidence: "
            + json.dumps(evidence, sort_keys=True)
        )
        rows = []
        try:
            providers = self._reviewers(privacy)
        except Exception as exc:
            return [{
                "provider": "reviewer-discovery",
                "ok": False,
                "error": f"{type(exc).__name__}: {str(exc)[:2000]}",
                "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-12000:],
            }]
        for provider in providers:
            try:
                if provider == "ollama":
                    local = self._direct_local(prompt, "reasoning")
                    rows.append({"provider": local["provider"], "ok": True, "review": local["text"][:4000]})
                elif provider.startswith("ollama-model:"):
                    model = provider.split(":", 1)[1]
                    text = self.router.local(prompt, model=model, task="reasoning", keep_alive=0)
                    rows.append({"provider": provider, "ok": True, "review": str(text)[:4000]})
                else:
                    text = self.router.ask(provider, prompt)
                    rows.append({"provider": provider, "ok": True, "review": str(text)[:4000], "sanitized": True})
            except Exception as exc:
                rows.append({"provider": provider, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
        return rows

    def _discard_candidate(self, candidate_root: str | Path) -> None:
        candidate = Path(candidate_root).resolve()
        staging = getattr(self.development, "staging_root", None)
        if staging is None:
            return
        staging = Path(staging).resolve()
        candidate.relative_to(staging)
        if candidate.name.startswith("candidate-") and candidate.is_dir():
            shutil.rmtree(candidate, ignore_errors=True)

    def run(
        self,
        *,
        project: str,
        project_root: str,
        checks: list[str],
        frontend_url: str | None,
        privacy: str,
        components: list[str] | None = None,
        max_rounds: int = 2,
        apply_verified: bool = False,
        promote: Callable[[str], dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        max_rounds = max(1, min(int(max_rounds or 1), 3))
        phase = "initial_verification"
        initial = None
        current = None
        candidate_root = None
        rounds = []

        def infrastructure_error(status: str, error: dict[str, Any]) -> dict[str, Any]:
            result = {
                "version": self.VERSION,
                "project": project,
                "status": status,
                "phase": phase,
                "initial_verification": initial,
                "repair_rounds": rounds,
                "model_reviews": [],
                "verified": False,
                "rolled_back": bool(candidate_root),
                "rollback": (
                    "candidate discarded; live tree unchanged"
                    if candidate_root
                    else "not required; live tree was not modified"
                ),
                "live_project_modified": False,
                "error": error,
            }
            if self.memory:
                try:
                    self.memory.audit("self_heal", status, f"{project}:{phase}:{error.get('type')}")
                except Exception:
                    pass
            return result

        try:
            initial = self.verify_parallel(project_root, checks, frontend_url, full=True)
            current = initial
            if initial.get("verification_errors"):
                return infrastructure_error(
                    "verification_error",
                    {
                        "type": "VerificationLaneError",
                        "message": "one or more initial verification lanes failed to execute",
                        "lanes": list(initial.get("verification_errors") or []),
                    },
                )

            if initial.get("passed"):
                phase = "model_review"
                reviews = self.model_review(project, privacy, initial)
                return {
                    "version": self.VERSION,
                    "project": project,
                    "status": "healthy",
                    "phase": "complete",
                    "initial_verification": initial,
                    "repair_rounds": [],
                    "model_reviews": reviews,
                    "verified": True,
                    "live_project_modified": False,
                }

            phase = "candidate_stage"
            candidate = self.development.stage(project_root, [])
            candidate_root = str(candidate["candidate_root"])

            for round_no in range(1, max_rounds + 1):
                phase = f"round_{round_no}_diagnosis"
                failure_summary = self._sanitized_evidence(current)
                diagnosis_prompt = (
                    "Diagnose this KRISHNA verification failure. Focus on root cause, smallest safe repair, "
                    "and which files/tests are most relevant. Do not propose disabling tests. Evidence: "
                    + json.dumps(failure_summary, sort_keys=True)
                    + "\nComponents: " + json.dumps(list(components or []))
                )
                diagnosis = self._direct_local(diagnosis_prompt, "reasoning")

                phase = f"round_{round_no}_context"
                hints = list(components or []) + self._failed_steps(current)
                context = CandidateRepairGuard.collect_context(candidate_root, hints)
                if not context.get("files"):
                    raise RuntimeError("no repairable source context found")

                phase = f"round_{round_no}_repair"
                evidence = [{
                    "lane": "parallel-verification",
                    "report": self._sanitized_evidence(current),
                    "diagnosis": diagnosis["text"][:8000],
                }]
                repair_prompt = CandidateRepairGuard.prompt(evidence, context)
                repair = self._direct_local(repair_prompt, "coding")
                obj = self._json_object(repair["text"])
                files = CandidateRepairGuard.validate_patch(candidate_root, obj.get("files") or [])
                changed = CandidateRepairGuard.apply(candidate_root, files)

                phase = f"round_{round_no}_narrow_verification"
                narrow_checks = self._failed_steps(current) or list(checks[:1])
                # Candidate UI verification must inspect the isolated candidate, not the live runtime.
                # Passing the live frontend URL here would re-test the old UI and could falsely approve a patch.
                narrow = self.verify_parallel(candidate_root, narrow_checks, None, full=False)
                row = {
                    "round": round_no,
                    "diagnosis_provider": diagnosis["provider"],
                    "repair_provider": repair["provider"],
                    "summary": str(obj.get("summary") or "")[:3000],
                    "files": changed,
                    "narrow_verification": narrow,
                }
                rounds.append(row)
                if narrow.get("verification_errors"):
                    self._discard_candidate(candidate_root)
                    candidate_root = None
                    current = narrow
                    return infrastructure_error(
                        "verification_error",
                        {
                            "type": "VerificationLaneError",
                            "message": "one or more narrow verification lanes failed to execute",
                            "lanes": list(narrow.get("verification_errors") or []),
                        },
                    )
                if not narrow.get("passed"):
                    current = narrow
                    continue

                phase = f"round_{round_no}_full_verification"
                # Full candidate regression also uses the isolated preview. Live URL verification
                # belongs to initial health evidence and the post-apply gate only.
                full = self.verify_parallel(candidate_root, checks, None, full=True)
                row["full_regression_runtime_ui"] = full
                current = full
                if full.get("verification_errors"):
                    self._discard_candidate(candidate_root)
                    candidate_root = None
                    return infrastructure_error(
                        "verification_error",
                        {
                            "type": "VerificationLaneError",
                            "message": "one or more full verification lanes failed to execute",
                            "lanes": list(full.get("verification_errors") or []),
                        },
                    )
                if full.get("passed"):
                    phase = f"round_{round_no}_model_review"
                    reviews = self.model_review(project, privacy, full)
                    result = {
                        "version": self.VERSION,
                        "project": project,
                        "status": "verified_candidate",
                        "phase": "candidate_verified",
                        "initial_verification": initial,
                        "repair_rounds": rounds,
                        "candidate_root": candidate_root,
                        "model_reviews": reviews,
                        "verified": True,
                        "live_project_modified": False,
                    }
                    if apply_verified:
                        phase = "promotion"
                        if promote is None:
                            raise RuntimeError("promotion callback is required for apply_verified")
                        promotion = promote(candidate_root)
                        result["promotion"] = promotion
                        result["live_project_modified"] = bool(promotion.get("promoted"))
                        result["status"] = (
                            "verified_and_applied" if promotion.get("promoted")
                            else "rolled_back" if promotion.get("rolled_back")
                            else "verified_not_applied"
                        )
                        result["verified"] = bool(promotion.get("promoted"))
                    if self.memory:
                        self.memory.audit("self_heal", result["status"], project)
                    return result

            phase = "rejected_review"
            self._discard_candidate(candidate_root)
            candidate_root = None
            result = {
                "version": self.VERSION,
                "project": project,
                "status": "rejected",
                "phase": "complete",
                "initial_verification": initial,
                "repair_rounds": rounds,
                "model_reviews": self.model_review(project, privacy, current),
                "verified": False,
                "rolled_back": True,
                "rollback": "candidate discarded; live tree unchanged",
                "live_project_modified": False,
            }
            if self.memory:
                self.memory.audit("self_heal", "rejected", project)
            return result
        except Exception as exc:
            if candidate_root:
                try:
                    self._discard_candidate(candidate_root)
                except Exception:
                    pass
            error = {
                "type": type(exc).__name__,
                "message": str(exc)[:2000],
                "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-12000:],
            }
            return infrastructure_error("self_heal_error", error)
