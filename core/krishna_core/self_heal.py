from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import shutil
import time
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

    def verify_parallel(
        self,
        candidate_root: str | Path,
        checks: list[str],
        frontend_url: str | None = None,
        full: bool = False,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="krishna-verify") as pool:
            backend_future = pool.submit(self.development.verify, candidate_root, list(checks or []))
            frontend_future = pool.submit(self._frontend_verify, candidate_root, frontend_url, full)
            backend = backend_future.result()
            frontend = frontend_future.result()
        backend_passed = bool(backend.get("verified")) if checks else True
        passed = bool(backend_passed and frontend.get("passed", True))
        return {
            "parallel": True,
            "mode": "full" if full else "narrow",
            "backend": backend,
            "frontend": frontend,
            "passed": passed,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }

    def _direct_local(self, prompt: str, task: str) -> dict[str, Any]:
        status = self.router.local_model_status(task)
        model = str(status.get("selected_model") or status.get("primary_model") or "").strip()
        if not model:
            raise RuntimeError("no approved local Ollama model is available for " + task)
        text = self.router.local(prompt, model=model, task=task, keep_alive=0)
        return {"provider": "ollama-model:" + model, "model": model, "text": str(text or "")}

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
        for provider in self._reviewers(privacy):
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
        initial = self.verify_parallel(project_root, checks, frontend_url, full=True)
        if initial.get("passed"):
            return {
                "version": self.VERSION,
                "project": project,
                "status": "healthy",
                "initial_verification": initial,
                "repair_rounds": [],
                "model_reviews": self.model_review(project, privacy, initial),
                "verified": True,
                "live_project_modified": False,
            }

        candidate = self.development.stage(project_root, [])
        candidate_root = str(candidate["candidate_root"])
        rounds = []
        current = initial
        try:
            for round_no in range(1, max_rounds + 1):
                failure_summary = self._sanitized_evidence(current)
                diagnosis_prompt = (
                    "Diagnose this KRISHNA verification failure. Focus on root cause, smallest safe repair, "
                    "and which files/tests are most relevant. Do not propose disabling tests. Evidence: "
                    + json.dumps(failure_summary, sort_keys=True)
                    + "\nComponents: " + json.dumps(list(components or []))
                )
                diagnosis = self._direct_local(diagnosis_prompt, "reasoning")

                hints = list(components or []) + self._failed_steps(current)
                context = CandidateRepairGuard.collect_context(candidate_root, hints)
                if not context.get("files"):
                    raise RuntimeError("no repairable source context found")

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

                narrow_checks = self._failed_steps(current) or list(checks[:1])
                narrow = self.verify_parallel(candidate_root, narrow_checks, frontend_url, full=False)
                row = {
                    "round": round_no,
                    "diagnosis_provider": diagnosis["provider"],
                    "repair_provider": repair["provider"],
                    "summary": str(obj.get("summary") or "")[:3000],
                    "files": changed,
                    "narrow_verification": narrow,
                }
                rounds.append(row)
                if not narrow.get("passed"):
                    current = narrow
                    continue

                full = self.verify_parallel(candidate_root, checks, frontend_url, full=True)
                row["full_regression_runtime_ui"] = full
                current = full
                if full.get("passed"):
                    reviews = self.model_review(project, privacy, full)
                    result = {
                        "version": self.VERSION,
                        "project": project,
                        "status": "verified_candidate",
                        "initial_verification": initial,
                        "repair_rounds": rounds,
                        "candidate_root": candidate_root,
                        "model_reviews": reviews,
                        "verified": True,
                        "live_project_modified": False,
                    }
                    if apply_verified:
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

            self._discard_candidate(candidate_root)
            result = {
                "version": self.VERSION,
                "project": project,
                "status": "rejected",
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
        except Exception:
            self._discard_candidate(candidate_root)
            raise
