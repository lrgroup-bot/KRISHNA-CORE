from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .project_perfection import ElementGeometry, GateEvidence, ProjectPerfectionLoop, WorkItem
from .project_perfection_adapters import (
    ApiFuzzAdapter, ArtifactRetest, ChaosVerifier, MutationVerifier,
    RegressionGenerator, RouteStateGraph, VisualEditIntent,
)
from .project_perfection_execution import (
    ArtifactExecutor, CandidateStaticServer, DesignStudio, MutationRunner, RegressionPersister, SourceMapper,
    VisualBaselineStore, VisualCandidateEditor,
)


class ProjectPerfectionRuntime:
    """Execution bridge over KRISHNA's browser/development/project-quality systems."""

    def __init__(self, browser, development, max_workers: int = 8, state_root: str | Path | None = None):
        self.browser = browser
        self.development = development
        self.loop = ProjectPerfectionLoop(max_workers=max_workers)
        self.state_graph = RouteStateGraph()
        self.regressions = RegressionGenerator()
        self.api_fuzz = ApiFuzzAdapter()
        self.chaos = ChaosVerifier()
        self.mutation = MutationVerifier()
        self.artifacts = ArtifactRetest()
        self.visual_edit = VisualEditIntent()
        root=Path(state_root or (Path.cwd()/".krishna_state"/"project-perfection")).resolve()
        root.mkdir(parents=True,exist_ok=True)
        self.state_root=root
        self.regression_store=RegressionPersister()
        self.visual_baselines=VisualBaselineStore(root/"visual-baselines")
        self.mutation_runner=MutationRunner()
        self.artifact_executor=ArtifactExecutor()
        self.design_studio=DesignStudio(root/"design-studio")
        self.source_mapper=SourceMapper()
        self.visual_candidate_editor=VisualCandidateEditor()
        self.candidate_static=CandidateStaticServer()

    def plan_team(self, work: list[dict[str, Any]], deadline_minutes: float) -> dict[str, Any]:
        items = [WorkItem(
            id=str(x.get("id") or i),
            role=str(x.get("role") or "engineer"),
            estimate_minutes=float(x.get("estimate_minutes") or 1),
            dependencies=tuple(x.get("dependencies") or ()),
            parallelizable=bool(x.get("parallelizable", True)),
            critical=bool(x.get("critical", True)),
        ) for i, x in enumerate(work)]
        return asdict(self.loop.hr.plan(items, deadline_minutes, self.loop.max_workers))

    def browser_audit(self, url: str, screenshot_dir: str | None = None, viewports: list[int] | None = None) -> dict[str, Any]:
        report = self.browser.perfection_scan(url, viewports=viewports, screenshot_dir=screenshot_dir)
        geometry_findings=[]
        for view in report.get("viewports", []):
            rows=[ElementGeometry(**x) for x in view.get("geometry", [])]
            findings=self.loop.geometry.inspect(rows, int(view["width"]), int(view["height"]))
            geometry_findings.append({"width":view["width"],"findings":findings,"ok":not findings})
        report["geometry_findings"]=geometry_findings
        report["geometry_ok"]=all(x["ok"] for x in geometry_findings)
        report["ok"]=bool(report.get("ok") and report["geometry_ok"])
        return report

    def explore_and_generate(self, project: str, url: str, screenshot_dir: str | None = None,
                             max_controls: int = 200, max_pages: int = 40, max_depth: int = 4) -> dict[str, Any]:
        exploration=self.browser.crawl_application(
            url,screenshot_dir=screenshot_dir,max_pages=max_pages,max_depth=max_depth,
            max_controls_per_page=max_controls,allow_mutating=False,
        )
        graph={"nodes":list(exploration.get("nodes") or []),"edges":list(exploration.get("edges") or []),
               "node_count":len(exploration.get("nodes") or []),"edge_count":len(exploration.get("edges") or [])}
        regression=self.regressions.generate(project,graph)
        return {"exploration":exploration,"graph":graph,"regression_source":regression,
                "ok":bool(exploration.get("ok"))}

    def persist_generated_regressions(self, project_root: str, project: str, regression_source: str) -> dict[str, Any]:
        return self.regression_store.persist(project_root,project,regression_source)

    def accessibility_verify(self, url: str) -> dict[str, Any]:
        return self.browser.accessibility_scan(url)

    def browser_chaos_verify(self, url: str) -> dict[str, Any]:
        result=self.browser.chaos_scan(url)
        scenarios=result.get("scenarios") or []
        result["passed"]=bool(scenarios) and all(bool(x.get("survived")) for x in scenarios)
        return result

    def api_fuzz_verify(self, schema_url: str, base_url: str | None = None) -> dict[str, Any]:
        return self.api_fuzz.run(schema_url,base_url)

    def run_mutation_testing(self, candidate_root: str, checks: list[str], max_mutants: int=8) -> dict[str, Any]:
        return self.mutation_runner.run(
            candidate_root,
            lambda:self.development.verify(candidate_root,checks),
            max_mutants=max_mutants,
        )

    def mutation_score(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        return self.mutation.score(results)

    def compare_visual_baselines(self, project: str, browser_report: dict[str, Any],
                                 approve_missing: bool=False, threshold: float=0.001) -> dict[str, Any]:
        rows=[]
        for view in browser_report.get("viewports") or []:
            shot=view.get("screenshot")
            if not shot:
                rows.append({"width":view.get("width"),"passed":False,"reason":"screenshot_not_captured"})
                continue
            result=self.visual_baselines.compare(
                project,f"viewport-{view.get('width')}",shot,
                approve_missing=approve_missing,max_changed_ratio=threshold,
            )
            rows.append({"width":view.get("width"),**result})
        return {"results":rows,"passed":bool(rows) and all(bool(x.get("passed")) for x in rows)}

    def artifact_retest_contract(self, kind: str, artifact: str) -> dict[str, Any]:
        return self.artifacts.contract(kind,artifact)

    def retest_artifact(self, artifact: dict[str, Any]) -> dict[str, Any]:
        kind=str(artifact.get("kind") or "").strip().lower()
        path=artifact.get("path") or artifact.get("artifact")
        if kind=="exe":
            return self.artifact_executor.exe(path,health_url=artifact.get("health_url"),
                                              startup_seconds=float(artifact.get("startup_seconds") or 2),
                                              args=list(artifact.get("args") or []))
        if kind=="apk":
            return self.artifact_executor.apk(path,package_id=str(artifact.get("package_id") or "com.krishna.mobile"))
        if kind=="ios":
            return self.artifact_executor.ios(path,bundle_id=str(artifact.get("bundle_id") or ""))
        if kind=="web":
            url=str(artifact.get("url") or path or "")
            report=self.browser.inspect(url)
            return {"kind":"web","executed":True,"passed":bool(report.get("ok")),"report":report}
        raise ValueError("unsupported artifact kind")

    def retest_artifacts(self, artifacts: list[dict[str, Any]]) -> dict[str, Any]:
        rows=[]
        for item in artifacts:
            try: rows.append(self.retest_artifact(dict(item)))
            except Exception as exc:
                rows.append({"kind":item.get("kind"),"executed":False,"passed":False,
                             "error":f"{type(exc).__name__}: {exc}"})
        return {"artifacts":rows,"passed":bool(rows) and all(bool(x.get("passed")) for x in rows)}

    def design_save_preview(self, project: str, html: str) -> dict[str, Any]:
        return self.design_studio.save_preview(project,html)

    def design_preview(self, token: str) -> str:
        return self.design_studio.preview(token)

    def design_create(self, project: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        return self.design_studio.create(project,candidates)

    def design_get(self, session_id: str) -> dict[str, Any]:
        return self.design_studio.get(session_id)

    def design_annotate(self, session_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
        return self.design_studio.annotate(session_id,metadata)

    def design_submit(self, session_id: str, candidate_id: str) -> dict[str, Any]:
        return self.design_studio.submit(session_id,candidate_id)

    def verify_design_candidate(self, project: str, candidate_root: str, checks: list[str],
                                frontend_url: str | None=None, approve_selected_baseline: bool=True) -> dict[str, Any]:
        """Verify the selected design against the candidate itself when a static preview is possible."""
        def run(target_url: str | None, preview: dict[str,Any]):
            dev=self.development.verify(candidate_root,checks,frontend_url=target_url)
            if not target_url:
                return {"passed":False,"development":dev,"preview":preview,
                        "reason":"candidate_browser_preview_unavailable"}
            shots=str(self.state_root/"design-verification"/project)
            exploration=self.explore_and_generate(project,target_url,screenshot_dir=shots,max_pages=25,max_depth=3)
            browser=self.browser_audit(target_url,screenshot_dir=shots)
            accessibility=self.accessibility_verify(target_url)
            chaos=self.browser_chaos_verify(target_url)
            visual=self.compare_visual_baselines(
                project,browser,approve_missing=approve_selected_baseline,threshold=0.001,
            )
            passed=all((
                bool(dev.get("verified")),bool(exploration.get("ok")),bool(browser.get("ok")),
                bool(accessibility.get("passed")),bool(chaos.get("passed")),bool(visual.get("passed")),
            ))
            return {"passed":passed,"development":dev,"preview":preview,
                    "exploration":exploration,"browser":browser,"accessibility":accessibility,
                    "chaos":chaos,"visual":visual}
        if frontend_url:
            return run(frontend_url,{"available":True,"url":frontend_url,"source":"registered_candidate_url"})
        with self.candidate_static.serve(candidate_root) as preview:
            return run(preview.get("url"),preview)

    def visual_edit_intent(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.visual_edit.normalize(payload)

    def visual_source_map(self, project_root: str, element: dict[str, Any], limit: int=20) -> dict[str, Any]:
        return self.source_mapper.find(project_root,element,limit)

    def stage_visual_edit(self, project_root: str, element: dict[str, Any], payload: dict[str, Any],
                          checks: list[str] | None=None) -> dict[str, Any]:
        intent=self.visual_edit.normalize(payload)
        if payload.get("replacement_text") is not None:intent["replacement_text"]=str(payload.get("replacement_text"))
        if payload.get("style_patch") is not None:intent["style_patch"]=dict(payload.get("style_patch") or {})
        mapping=self.source_mapper.find(project_root,element)
        staged=self.development.stage(project_root,[])
        candidate=staged["candidate_root"]
        applied=self.visual_candidate_editor.apply(candidate,element,intent,mapping)
        verification=None
        if applied.get("applied") and checks:
            verification=self.development.verify(candidate,list(checks))
        return {"intent":intent,"source_map":mapping,"staged":staged,"candidate_root":candidate,
                "edit":applied,"verification":verification,
                "promotable":bool(applied.get("applied") and verification and verification.get("verified"))}

    def completion_certificate(self, project: str, build_hash: str, gates: list[dict[str, Any]],
                               mutation_detection: float | None = None) -> dict[str, Any]:
        evidence=[GateEvidence(
            gate=str(x.get("gate") or ""),
            passed=bool(x.get("passed")),
            evidence=[str(v) for v in x.get("evidence") or []],
            critical_failures=[str(v) for v in x.get("critical_failures") or []],
        ) for x in gates]
        return self.loop.completion.certify(project, build_hash, evidence, mutation_detection)

    def finish_project(self, project: str, project_root: str, url: str, build_hash: str,
                       checks: list[str], requirements_ok: bool,
                       schema_url: str | None=None, api_base_url: str | None=None,
                       artifacts: list[dict[str, Any]] | None=None,
                       screenshot_dir: str | None=None, approve_visual_baselines: bool=False,
                       backend_required: bool=True, artifact_required: bool=False,
                       security_ok: bool=False, restart_recovery_ok: bool=False,
                       max_mutants: int=8, deadline_minutes: float=60.0,
                       work_items: list[dict[str, Any]] | None=None) -> dict[str, Any]:
        """Run the full evidence pipeline once. Failed/missing evidence never becomes COMPLETE."""
        root=Path(project_root).resolve()
        default_work=[
            {"id":"browser","role":"browser_qa","estimate_minutes":12},
            {"id":"geometry","role":"ui_qa","estimate_minutes":10},
            {"id":"accessibility","role":"accessibility_qa","estimate_minutes":7},
            {"id":"api","role":"backend_qa","estimate_minutes":10},
            {"id":"adversarial","role":"adversarial_qa","estimate_minutes":12},
            {"id":"artifact","role":"release_qa","estimate_minutes":10},
            {"id":"certificate","role":"independent_verifier","estimate_minutes":5,"parallelizable":False},
        ]
        team_plan=self.plan_team(list(work_items or default_work),deadline_minutes)
        staged=self.development.stage(root,[])
        candidate_root=Path(staged["candidate_root"]).resolve()
        shots=screenshot_dir or str(self.state_root/"runs"/project)
        exploration=self.explore_and_generate(project,url,screenshot_dir=shots)
        regression=self.persist_generated_regressions(candidate_root,project,exploration["regression_source"])
        browser=self.browser_audit(url,screenshot_dir=shots)
        accessibility=self.accessibility_verify(url)
        chaos=self.browser_chaos_verify(url)
        dev=self.development.verify(candidate_root,checks,frontend_url=url)
        mutation=self.run_mutation_testing(candidate_root,checks,max_mutants=max_mutants) if checks else {"executed":0,"passed":False,"score":None}
        visual=self.compare_visual_baselines(project,browser,approve_missing=approve_visual_baselines)
        api=self.api_fuzz_verify(schema_url,api_base_url) if schema_url else {
            "available":False,"passed":not backend_required,
            "reason":"not_applicable" if not backend_required else "api_schema_or_backend_verification_required",
        }
        artifact_rows=list(artifacts or [])
        package_build=bool(artifact_rows) and all(Path(str(x.get("path") or x.get("artifact") or "")).exists() for x in artifact_rows)
        installed=self.retest_artifacts(artifact_rows) if artifact_rows else {
            "artifacts":[],"passed":not artifact_required,
            "reason":"not_applicable" if not artifact_required else "artifact_required",
        }

        gates=[
            {"gate":"requirements","passed":bool(requirements_ok),"evidence":["requirements ledger acknowledged"] if requirements_ok else []},
            {"gate":"unit","passed":bool(dev.get("verified")) and bool(checks),"evidence":[str(dev.get("steps") or [])]},
            {"gate":"integration","passed":bool(dev.get("verified")),"evidence":[str(dev.get("frontend_backend_connected"))]},
            {"gate":"backend_api","passed":bool(api.get("passed")),"evidence":[str(api.get("reason") or api.get("exit_code") or "")]},
            {"gate":"browser_e2e","passed":bool(exploration.get("ok")),"evidence":[f"nodes={exploration['graph']['node_count']} edges={exploration['graph']['edge_count']}"]},
            {"gate":"ui_geometry","passed":bool(browser.get("geometry_ok")),"evidence":[str(browser.get("geometry_findings") or [])]},
            {"gate":"visual_regression","passed":bool(visual.get("passed")),"evidence":[str(visual.get("results") or [])]},
            {"gate":"responsive","passed":bool(browser.get("ok")),"evidence":[str([x.get("width") for x in browser.get("viewports") or []])]},
            {"gate":"accessibility","passed":bool(accessibility.get("passed")),"evidence":[str(accessibility.get("issues") or [])]},
            {"gate":"security","passed":bool(security_ok),"evidence":["KABACH/independent security gate supplied"] if security_ok else []},
            {"gate":"adversarial","passed":bool(chaos.get("passed")) and bool(mutation.get("passed")),
             "evidence":[str(chaos.get("scenarios") or []),str({"mutation_score":mutation.get("score")})]},
            {"gate":"restart_recovery","passed":bool(restart_recovery_ok),"evidence":["restart/recovery verification supplied"] if restart_recovery_ok else []},
            {"gate":"package_build","passed":package_build or not artifact_required,
             "evidence":[str([x.get("path") or x.get("artifact") for x in artifact_rows])]},
            {"gate":"installed_artifact","passed":bool(installed.get("passed")),"evidence":[str(installed.get("artifacts") or installed.get("reason") or "")]},
        ]
        cert=self.completion_certificate(project,build_hash,gates,mutation.get("score"))
        return {
            "project":project,"team_plan":team_plan,
            "candidate_root":str(candidate_root),"staged":staged,
            "certificate":cert,"requirements_ok":requirements_ok,
            "exploration":exploration,"regression":regression,"browser":browser,
            "accessibility":accessibility,"chaos":chaos,"development":dev,
            "mutation":mutation,"visual":visual,"api_fuzz":api,
            "artifacts":installed,"gates":gates,
            "verdict":cert["verdict"],"passed":cert["passed"],
        }

    def immunize_bug(self, project: str, trigger: str, root_cause: str, regression_test: str, verification: str) -> dict[str, Any]:
        return asdict(self.loop.immune.immunize(project, trigger, root_cause, regression_test, verification))

    def status(self) -> dict[str, Any]:
        out=self.loop.status()
        out["state_root"]=str(self.state_root)
        out["execution"]={
            "recursive_crawl":True,"accessibility_scan":True,"browser_chaos":True,
            "regression_persistence":True,"mutation_runner":True,"visual_baselines":True,
            "artifact_executors":["exe","apk","ios","web"],"design_studio":True,
            "point_to_source_mapping":True,"candidate_visual_edit":True,
            "finish_project_pipeline":True,
        }
        return out
