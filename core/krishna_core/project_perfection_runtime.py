from __future__ import annotations

from contextlib import nullcontext
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .project_perfection import ElementGeometry, GateEvidence, ProjectPerfectionLoop, WorkItem
from .hawkeye_ui_reviewer import HawkeyeUIReviewer
from .project_perfection_adapters import (
    ApiFuzzAdapter, ArtifactRetest, ChaosVerifier, MutationVerifier,
    RegressionGenerator, RouteStateGraph, VisualEditIntent,
)
from .project_perfection_execution import (
    ArtifactExecutor, BrowserRegressionRunner, CandidateStaticServer, DesignStudio, MutationRunner,
    RegressionManifest, RegressionPersister, SourceMapper, VisualBaselineStore, VisualCandidateEditor,
)


class ProjectPerfectionRuntime:
    """Execution bridge over KRISHNA's browser/development/project-quality systems."""

    def __init__(self, browser, development, max_workers: int = 8, state_root: str | Path | None = None):
        self.browser = browser
        self.development = development
        root=Path(state_root or (Path.cwd()/".krishna_state"/"project-perfection")).resolve()
        root.mkdir(parents=True,exist_ok=True)
        self.state_root=root
        self.loop = ProjectPerfectionLoop(max_workers=max_workers,immune_path=root/"immune-memory.json")
        self.state_graph = RouteStateGraph()
        self.regressions = RegressionGenerator()
        self.api_fuzz = ApiFuzzAdapter()
        self.chaos = ChaosVerifier()
        self.mutation = MutationVerifier()
        self.artifacts = ArtifactRetest()
        self.visual_edit = VisualEditIntent()
        self.regression_store=RegressionPersister()
        self.regression_manifest=RegressionManifest()
        self.regression_runner=BrowserRegressionRunner()
        self.visual_baselines=VisualBaselineStore(root/"visual-baselines")
        self.mutation_runner=MutationRunner()
        self.artifact_executor=ArtifactExecutor()
        self.design_studio=DesignStudio(root/"design-studio")
        self.source_mapper=SourceMapper()
        self.visual_candidate_editor=VisualCandidateEditor()
        self.candidate_static=CandidateStaticServer()
        self.hawkeye_ui=HawkeyeUIReviewer()

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
        """Run mutation testing against code checks and, when possible, the isolated rendered candidate."""
        with self.candidate_static.serve(candidate_root) as preview:
            preview_url=preview.get("url")
            def verify():
                dev=self.development.verify(candidate_root,checks)
                browser=None
                browser_ok=True
                if preview_url:
                    try:
                        browser=self.browser_audit(preview_url,viewports=[390,1440])
                        browser_ok=bool(browser.get("ok") and browser.get("geometry_ok"))
                    except Exception as exc:
                        browser={"ok":False,"error":f"{type(exc).__name__}: {exc}"}
                        browser_ok=False
                checks_ok=bool(dev.get("verified")) if checks else True
                return {
                    "verified":bool(checks_ok and browser_ok),
                    "development":dev,
                    "browser":browser,
                    "candidate_preview":preview,
                }
            result=self.mutation_runner.run(candidate_root,verify,max_mutants=max_mutants)
            result["candidate_preview"]=preview
            result["verification_scope"]={
                "code_checks":list(checks or []),
                "rendered_candidate":bool(preview_url),
            }
            return result

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

    @staticmethod
    def performance_verify(browser_report: dict[str,Any], limits: dict[str,float] | None=None,
                           required: bool=False) -> dict[str,Any]:
        thresholds=dict(limits or {"load_ms":10000.0,"dom_content_loaded_ms":7000.0})
        rows=[];violations=[]
        for view in browser_report.get("viewports") or []:
            perf=dict(view.get("performance") or {})
            row={"width":view.get("width"),"metrics":perf};rows.append(row)
            if required:
                for metric,limit in thresholds.items():
                    value=perf.get(metric)
                    if value is None:
                        violations.append({"width":view.get("width"),"metric":metric,"reason":"metric_missing"})
                    elif float(value)>float(limit):
                        violations.append({"width":view.get("width"),"metric":metric,
                                           "value":float(value),"limit":float(limit)})
        return {"required":bool(required),"thresholds":thresholds,"views":rows,
                "violations":violations,"passed":not required or not violations}

    def hawkeye_ui_verify(self, exploration: dict[str,Any], browser: dict[str,Any],
                           accessibility: dict[str,Any] | None=None, required: bool=False) -> dict[str,Any]:
        images=[]
        crawl=(exploration.get("exploration") or exploration or {})
        for node in crawl.get("nodes") or []:
            if node.get("screenshot"):
                images.append({"path":node["screenshot"],"label":node.get("url") or node.get("title") or "page"})
        preferred=(390,1440,1920)
        views=list(browser.get("viewports") or [])
        views.sort(key=lambda x:(0 if x.get("width") in preferred else 1, abs(int(x.get("width") or 0)-1440)))
        for view in views:
            if view.get("screenshot"):
                images.append({"path":view["screenshot"],"label":f"viewport-{view.get('width')}"})
        context={
            "geometry_findings":browser.get("geometry_findings") or [],
            "browser_findings":[
                {"width":v.get("width"),"findings":v.get("findings") or [],"layout":v.get("layout") or {}}
                for v in views
            ],
            "accessibility_issues":(accessibility or {}).get("issues") or [],
        }
        return self.hawkeye_ui.review(images,context,required=required)

    def verify_design_candidate(self, project: str, candidate_root: str, checks: list[str],
                                frontend_url: str | None=None, approve_selected_baseline: bool=True,
                                axe_required: bool=False, performance_required: bool=False,
                                performance_limits: dict[str,float] | None=None,
                                hawkeye_required: bool=False) -> dict[str, Any]:
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
            performance=self.performance_verify(browser,performance_limits,performance_required)
            chaos=self.browser_chaos_verify(target_url)
            hawkeye=self.hawkeye_ui_verify(exploration,browser,accessibility,required=hawkeye_required)
            # User selection explicitly approves a *new* visual direction, so the old
            # project golden baseline is not used to reject the intentional redesign.
            visual_candidate={"results":[],"passed":True}
            for view in browser.get("viewports") or []:
                if not view.get("screenshot"):
                    visual_candidate["passed"]=False
                    visual_candidate["results"].append({"width":view.get("width"),"passed":False,"reason":"screenshot_not_captured"})
                    continue
                visual_candidate["results"].append({
                    "width":view.get("width"),
                    "candidate":view.get("screenshot"),
                    "passed":True,
                })
            accessibility_ok=bool(accessibility.get("passed")) and (
                not axe_required or bool((accessibility.get("axe") or {}).get("available"))
            )
            passed=all((
                bool(dev.get("verified")),bool(exploration.get("ok")),bool(browser.get("ok")),
                accessibility_ok,bool(performance.get("passed")),bool(chaos.get("passed")),
                bool(hawkeye.get("passed")),bool(visual_candidate.get("passed")),
            ))
            baseline_approval=[]
            if passed and approve_selected_baseline:
                for view in browser.get("viewports") or []:
                    if view.get("screenshot"):
                        baseline_approval.append(self.visual_baselines.approve(
                            project,f"viewport-{view.get('width')}",view["screenshot"],
                        ))
            return {"passed":passed,"development":dev,"preview":preview,
                    "exploration":exploration,"browser":browser,"accessibility":accessibility,
                    "performance":performance,"chaos":chaos,"hawkeye":hawkeye,"visual":visual_candidate,
                    "accessibility_strict_required":bool(axe_required),
                    "hawkeye_required":bool(hawkeye_required),
                    "baseline_approval":baseline_approval}
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

    def post_apply_verify(self, project: str, project_root: str, url: str, checks: list[str],
                          axe_required: bool=True, performance_required: bool=True,
                          performance_limits: dict[str,float] | None=None,
                          hawkeye_required: bool=False) -> dict[str, Any]:
        """Read-only verification of the live tree after transactional promotion."""
        root=Path(project_root).resolve()
        dev=self.development.verify(root,list(checks or []),frontend_url=url)
        manifest=self.regression_manifest.load(root,project)
        regression=self.regression_runner.run(self.browser,url,manifest)
        shots=str(self.state_root/"post-apply"/project)
        browser=self.browser_audit(url,screenshot_dir=shots)
        accessibility=self.accessibility_verify(url)
        performance=self.performance_verify(browser,performance_limits,performance_required)
        chaos=self.browser_chaos_verify(url)
        hawkeye=self.hawkeye_ui_verify({"exploration":{"nodes":[]}},browser,accessibility,required=hawkeye_required)
        accessibility_ok=bool(accessibility.get("passed")) and (
            not axe_required or bool((accessibility.get("axe") or {}).get("available"))
        )
        passed=all((
            bool(dev.get("verified")),
            bool(regression.get("passed")),
            bool(browser.get("ok")),
            accessibility_ok,
            bool(performance.get("passed")),
            bool(chaos.get("passed")),
            bool(hawkeye.get("passed")),
        ))
        return {
            "passed":passed,"development":dev,"regression":regression,"browser":browser,
            "accessibility":accessibility,"performance":performance,"chaos":chaos,"hawkeye":hawkeye,
            "axe_required":bool(axe_required),"hawkeye_required":bool(hawkeye_required),
            "live_root":str(root),"url":url,
        }

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
                       work_items: list[dict[str, Any]] | None=None,
                       use_candidate_static_preview: bool=False,
                       restart_recovery_required: bool=True,
                       axe_required: bool=False,
                       performance_required: bool=False,
                       performance_limits: dict[str,float] | None=None,
                       hawkeye_required: bool=False) -> dict[str, Any]:
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
        preview_context=self.candidate_static.serve(candidate_root) if use_candidate_static_preview else nullcontext({
            "available":True,"url":url,"source":"provided_runtime_url",
        })
        with preview_context as candidate_preview:
            effective_url=candidate_preview.get("url")
            previous_manifest=self.regression_manifest.load(candidate_root,project)
            if effective_url:
                prior_regression=self.regression_runner.run(self.browser,effective_url,previous_manifest)
                exploration=self.explore_and_generate(project,effective_url,screenshot_dir=shots)
                regression_source=self.persist_generated_regressions(
                    candidate_root,project,exploration.get("regression_source") or ""
                )
                regression_manifest=self.regression_manifest.persist(
                    candidate_root,project,exploration.get("graph") or {}
                )
                current_manifest=self.regression_manifest.load(candidate_root,project)
                current_regression=self.regression_runner.run(self.browser,effective_url,current_manifest)
                browser=self.browser_audit(effective_url,screenshot_dir=shots)
                accessibility=self.accessibility_verify(effective_url)
                performance=self.performance_verify(browser,performance_limits,performance_required)
                chaos=self.browser_chaos_verify(effective_url)
                hawkeye=self.hawkeye_ui_verify(exploration,browser,accessibility,required=hawkeye_required)
                dev=self.development.verify(candidate_root,checks,frontend_url=effective_url)
                visual=self.compare_visual_baselines(project,browser,approve_missing=approve_visual_baselines)
            else:
                prior_regression={"available":bool(previous_manifest),"passed":False,"reason":"candidate_preview_unavailable","routes":[]}
                current_regression={"available":False,"passed":False,"reason":"candidate_preview_unavailable","routes":[]}
                exploration={"ok":False,"graph":{"node_count":0,"edge_count":0},"regression_source":"",
                             "reason":"candidate_preview_unavailable","exploration":{"findings":[]}}
                regression_source={"persisted":False,"reason":"candidate_preview_unavailable"}
                regression_manifest={"persisted":False,"reason":"candidate_preview_unavailable"}
                browser={"ok":False,"geometry_ok":False,"viewports":[],"geometry_findings":[],
                         "reason":"candidate_preview_unavailable"}
                accessibility={"passed":False,"issues":[{"kind":"candidate_preview_unavailable"}]}
                performance={"required":bool(performance_required),"passed":not performance_required,
                             "violations":[{"reason":"candidate_preview_unavailable"}] if performance_required else []}
                chaos={"passed":False,"scenarios":[],"reason":"candidate_preview_unavailable"}
                hawkeye={"available":False,"required":bool(hawkeye_required),"passed":not hawkeye_required,
                         "reason":"candidate_preview_unavailable","reviews":[],"issues":[]}
                dev=self.development.verify(candidate_root,checks)
                visual={"passed":False,"results":[],"reason":"candidate_preview_unavailable"}
        regression={"source":regression_source,"manifest":regression_manifest,
                    "prior":prior_regression,"current":current_regression}
        mutation=self.run_mutation_testing(candidate_root,checks,max_mutants=max_mutants)
        api=self.api_fuzz_verify(schema_url,api_base_url) if schema_url else {
            "available":False,"passed":not backend_required,
            "reason":"not_applicable" if not backend_required else "api_schema_or_backend_verification_required",
        }
        artifact_rows=list(artifacts or [])
        def artifact_exists(item):
            kind=str(item.get("kind") or "").lower()
            if kind=="web":
                return bool(str(item.get("url") or item.get("path") or "").startswith(("http://","https://")))
            return Path(str(item.get("path") or item.get("artifact") or "")).exists()
        package_build=bool(artifact_rows) and all(artifact_exists(x) for x in artifact_rows)
        installed=self.retest_artifacts(artifact_rows) if artifact_rows else {
            "artifacts":[],"passed":not artifact_required,
            "reason":"not_applicable" if not artifact_required else "artifact_required",
        }
        def restart_evidence(row):
            kind=str(row.get("kind") or "").lower()
            if kind=="exe":
                return any(x.get("cycle")=="restart" and x.get("passed") for x in row.get("runs") or [])
            if kind in {"apk","ios"}:
                return any(x.get("name")=="restart" and x.get("passed") for x in row.get("steps") or [])
            if kind=="web":
                return bool((row.get("report") or {}).get("ok"))
            return False
        artifact_restart_ok=bool(installed.get("artifacts")) and all(restart_evidence(x) for x in installed.get("artifacts") or [])
        effective_restart_ok=(not restart_recovery_required) or (
            artifact_restart_ok if installed.get("artifacts") else bool(restart_recovery_ok)
        )

        gates=[
            {"gate":"requirements","passed":bool(requirements_ok),"evidence":["requirements ledger acknowledged"] if requirements_ok else []},
            {"gate":"unit","passed":bool(dev.get("verified")) and bool(checks),"evidence":[str(dev.get("steps") or [])]},
            {"gate":"integration","passed":bool(dev.get("verified")),"evidence":[str(dev.get("frontend_backend_connected"))]},
            {"gate":"backend_api","passed":bool(api.get("passed")),"evidence":[str(api.get("reason") or api.get("exit_code") or "")]},
            {"gate":"browser_e2e","passed":bool(exploration.get("ok")) and bool(prior_regression.get("passed")) and bool(current_regression.get("passed")),
             "evidence":[f"nodes={exploration['graph']['node_count']} edges={exploration['graph']['edge_count']}",
                         str({"prior_regression":prior_regression.get("passed"),"prior_routes":prior_regression.get("route_count",0),
                              "current_regression":current_regression.get("passed"),"current_routes":current_regression.get("route_count",0)})]},
            {"gate":"ui_geometry","passed":bool(browser.get("geometry_ok")),"evidence":[str(browser.get("geometry_findings") or [])]},
            {"gate":"visual_regression","passed":bool(visual.get("passed")) and bool(hawkeye.get("passed")),
             "evidence":[str(visual.get("results") or []),
                         str({"hawkeye_available":hawkeye.get("available"),"hawkeye_required":bool(hawkeye_required),
                              "hawkeye_passed":hawkeye.get("passed"),"material_issues":hawkeye.get("material_issues") or []})]},
            {"gate":"responsive","passed":bool(browser.get("ok")),"evidence":[str([x.get("width") for x in browser.get("viewports") or []])]},
            {"gate":"performance","passed":bool(performance.get("passed")),
             "evidence":[str({"required":performance.get("required"),"thresholds":performance.get("thresholds"),
                              "violations":performance.get("violations")})]},
            {"gate":"accessibility","passed":bool(accessibility.get("passed")) and (not axe_required or bool((accessibility.get("axe") or {}).get("available"))),
             "evidence":[str({"semantic_issues":accessibility.get("issues") or [],
                              "axe_available":bool((accessibility.get("axe") or {}).get("available")),
                              "axe_violations":(accessibility.get("axe") or {}).get("violations") or [],
                              "axe_required":bool(axe_required)})]},
            {"gate":"security","passed":bool(security_ok),"evidence":["KABACH/independent security gate supplied"] if security_ok else []},
            {"gate":"adversarial","passed":bool(chaos.get("passed")) and bool(mutation.get("passed")),
             "evidence":[str(chaos.get("scenarios") or []),str({"mutation_score":mutation.get("score")})]},
            {"gate":"restart_recovery","passed":bool(effective_restart_ok),
             "evidence":[str({"required":bool(restart_recovery_required),"artifact_restart":artifact_restart_ok,
                              "external_restart_evidence":bool(restart_recovery_ok)})]},
            {"gate":"package_build","passed":package_build or not artifact_required,
             "evidence":[str([x.get("path") or x.get("artifact") for x in artifact_rows])]},
            {"gate":"installed_artifact","passed":bool(installed.get("passed")),"evidence":[str(installed.get("artifacts") or installed.get("reason") or "")]},
        ]
        cert=self.completion_certificate(project,build_hash,gates,mutation.get("score"))
        return {
            "project":project,"team_plan":team_plan,"candidate_preview":candidate_preview,
            "effective_url":candidate_preview.get("url") if candidate_preview else url,
            "candidate_root":str(candidate_root),"staged":staged,
            "certificate":cert,"requirements_ok":requirements_ok,
            "exploration":exploration,"regression":regression,"browser":browser,
            "accessibility":accessibility,"performance":performance,"chaos":chaos,"hawkeye":hawkeye,"development":dev,
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
            "point_to_source_mapping":True,"candidate_visual_edit":True,"hawkeye_ui_review":True,
            "finish_project_pipeline":True,
        }
        return out
