from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .project_perfection import ElementGeometry, GateEvidence, ProjectPerfectionLoop, WorkItem
from .project_perfection_adapters import (
    ApiFuzzAdapter, ArtifactRetest, ChaosVerifier, MutationVerifier,
    RegressionGenerator, RouteStateGraph, VisualEditIntent,
)


class ProjectPerfectionRuntime:
    """Runtime bridge over KRISHNA's existing browser/development/worker systems."""

    def __init__(self, browser, development, max_workers: int = 8):
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

    def explore_and_generate(self, project: str, url: str, screenshot_dir: str | None = None, max_controls: int = 200) -> dict[str, Any]:
        exploration=self.browser.exhaustive_clickthrough(url,screenshot_dir=screenshot_dir,max_controls=max_controls)
        graph=self.state_graph.build(exploration)
        regression=self.regressions.generate(project,graph)
        return {"exploration":exploration,"graph":graph,"regression_source":regression,
                "ok":bool(exploration.get("ok"))}

    def api_fuzz_verify(self, schema_url: str, base_url: str | None = None) -> dict[str, Any]:
        return self.api_fuzz.run(schema_url,base_url)

    def mutation_score(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        return self.mutation.score(results)

    def artifact_retest_contract(self, kind: str, artifact: str) -> dict[str, Any]:
        return self.artifacts.contract(kind,artifact)

    def visual_edit_intent(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.visual_edit.normalize(payload)

    def completion_certificate(self, project: str, build_hash: str, gates: list[dict[str, Any]], mutation_detection: float | None = None) -> dict[str, Any]:
        evidence=[GateEvidence(
            gate=str(x.get("gate") or ""),
            passed=bool(x.get("passed")),
            evidence=[str(v) for v in x.get("evidence") or []],
            critical_failures=[str(v) for v in x.get("critical_failures") or []],
        ) for x in gates]
        return self.loop.completion.certify(project, build_hash, evidence, mutation_detection)

    def immunize_bug(self, project: str, trigger: str, root_cause: str, regression_test: str, verification: str) -> dict[str, Any]:
        return asdict(self.loop.immune.immunize(project, trigger, root_cause, regression_test, verification))

    def status(self) -> dict[str, Any]:
        return self.loop.status()
