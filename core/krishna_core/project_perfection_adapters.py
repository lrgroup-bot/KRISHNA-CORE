from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import json
import importlib.util
import shutil
import subprocess
import sys
import time
import urllib.request


@dataclass
class StateNode:
    key: str
    url: str
    title: str
    depth: int
    controls: int = 0


@dataclass
class StateEdge:
    source: str
    target: str
    action: str
    label: str = ""


class RouteStateGraph:
    """Build a deterministic, bounded graph from browser exploration evidence."""

    def build(self, exploration: dict[str, Any]) -> dict[str, Any]:
        nodes: dict[str, StateNode] = {}
        edges: list[StateEdge] = []
        start=str(exploration.get("url") or "")
        def key(url: str) -> str:
            return sha256(url.encode()).hexdigest()[:16]
        if start:
            nodes[key(start)]=StateNode(key(start),start,str(exploration.get("title") or ""),0)
        for row in exploration.get("evidence") or []:
            before=str(row.get("before") or start); after=str(row.get("after") or before)
            if before:
                nodes.setdefault(key(before),StateNode(key(before),before,"",0))
            if after:
                nodes.setdefault(key(after),StateNode(key(after),after,"",1 if after!=start else 0))
            if before and after:
                edges.append(StateEdge(key(before),key(after),"click",str(row.get("label") or "")))
        return {"nodes":[asdict(x) for x in nodes.values()],"edges":[asdict(x) for x in edges],
                "node_count":len(nodes),"edge_count":len(edges)}


class RegressionGenerator:
    """Generate portable Playwright regression source from discovered route nodes."""

    @staticmethod
    def _route(url: str) -> str:
        p=urlparse(str(url or ""))
        route=p.path or "/"
        if p.query:route+="?"+p.query
        return route

    def generate(self, project: str, graph: dict[str, Any]) -> str:
        routes=sorted({self._route(x["url"]) for x in graph.get("nodes") or [] if str(x.get("url") or "").startswith(("http://","https://"))})
        lines=["import { test, expect } from '@playwright/test';","",
               "const baseURL = process.env.KRISHNA_BASE_URL;",
               "if (!baseURL) throw new Error('KRISHNA_BASE_URL is required for generated regressions');","",
               f"test.describe({json.dumps('KRISHNA generated regression: '+project)}, () => {{"]
        for i,route in enumerate(routes):
            lines += [f"  test('route {i+1}', async ({{ page }}) => {{",
                      f"    const errors: string[] = [];",
                      "    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });",
                      f"    await page.goto(new URL({json.dumps(route)}, baseURL).toString(), {{ waitUntil: 'domcontentloaded' }});",
                      "    await expect(page.locator('body')).toBeVisible();",
                      "    expect(errors).toEqual([]);",
                      "  });"]
        lines += ["});",""]
        return "\n".join(lines)


class ApiFuzzAdapter:
    """Optional Schemathesis adapter; absent dependency is explicit, never silently passed."""

    def run(self, schema_url: str, base_url: str | None = None, timeout: int = 300) -> dict[str, Any]:
        cli=shutil.which("schemathesis")
        if cli:
            args=[cli,"run",schema_url]
        elif not getattr(sys,"frozen",False) and importlib.util.find_spec("schemathesis") is not None:
            args=[sys.executable,"-m","schemathesis","run",schema_url]
        else:
            return {"available":False,"passed":False,"reason":"schemathesis_unavailable"}
        if base_url: args += ["--base-url",base_url]
        started=time.perf_counter()
        try:
            p=subprocess.run(args,capture_output=True,text=True,timeout=timeout,shell=False)
            return {"available":True,"passed":p.returncode==0,"exit_code":p.returncode,
                    "command":args[:2],"output":((p.stdout or "")+"\n"+(p.stderr or ""))[-20000:],
                    "elapsed_ms":int((time.perf_counter()-started)*1000)}
        except FileNotFoundError as exc:
            return {"available":False,"passed":False,"error":str(exc)}
        except subprocess.TimeoutExpired:
            return {"available":True,"passed":False,"error":"api fuzz timeout"}


class ChaosVerifier:
    """Safe failure probes for test environments; does not mutate production services."""

    def http_probe(self, url: str, timeout_seconds: float = 2.0) -> dict[str, Any]:
        started=time.perf_counter()
        try:
            with urllib.request.urlopen(url,timeout=timeout_seconds) as response:
                body=response.read(4096)
                return {"scenario":"http_probe","reachable":True,"status":response.status,
                        "body_sample":body.decode("utf-8","replace"),
                        "elapsed_ms":int((time.perf_counter()-started)*1000)}
        except Exception as exc:
            return {"scenario":"http_probe","reachable":False,"error":f"{type(exc).__name__}: {exc}",
                    "elapsed_ms":int((time.perf_counter()-started)*1000)}

    def scenario_contracts(self) -> list[dict[str, Any]]:
        return [
            {"name":"api_500","isolation_required":True},
            {"name":"api_timeout","isolation_required":True},
            {"name":"offline","isolation_required":True},
            {"name":"permission_denied","isolation_required":True},
            {"name":"service_restart","isolation_required":True},
            {"name":"double_submit","isolation_required":True},
        ]


class MutationVerifier:
    """Mutation contract: mutate only isolated candidates and require tests to fail."""

    def score(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        total=len(results); detected=sum(1 for x in results if bool(x.get("detected")))
        return {"total":total,"detected":detected,"score":(detected/total if total else None),
                "passed":bool(total and detected==total)}


class ArtifactRetest:
    """Describe and record clean-artifact retesting after packaging."""

    def contract(self, kind: str, artifact: str) -> dict[str, Any]:
        kind=kind.lower().strip()
        steps={
            "exe":["clean_sandbox","launch","health","ui_e2e","restart","persistence","logs"],
            "apk":["emulator_or_device","install","launch","permissions","ui_e2e","background_foreground","restart","logs"],
            "ios":["simulator_or_device","install","launch","permissions","ui_e2e","lifecycle","logs"],
            "web":["clean_browser_context","launch","ui_e2e","network","console","reload"],
        }
        if kind not in steps: raise ValueError("unsupported artifact kind")
        return {"kind":kind,"artifact":artifact,"steps":steps[kind],"required":True,
                "rule":"package build success alone is not release completion"}


class VisualEditIntent:
    """Validated point/drag/speak intent. Source patching remains DevelopmentOperator's job."""

    ALLOWED={"move","resize","remove","restyle","replace_text","add_component"}

    def normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        action=str(payload.get("action") or "").strip().lower()
        if action not in self.ALLOWED: raise ValueError("unsupported visual edit action")
        selector=str(payload.get("selector") or "").strip()
        if not selector: raise ValueError("selector is required")
        return {"action":action,"selector":selector,
                "from_box":payload.get("from_box"),"to_box":payload.get("to_box"),
                "instruction":str(payload.get("instruction") or "")[:2000],
                "source_hint":str(payload.get("source_hint") or "")[:1000],
                "requires_candidate_patch":True,"requires_regression":True}
