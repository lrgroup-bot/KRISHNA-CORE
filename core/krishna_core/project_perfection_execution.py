from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin, urlparse
import json
import os
import platform
import threading
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request


def _safe_slug(value: str) -> str:
    raw="".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in str(value or ""))
    return raw.strip("._")[:120] or "project"


class RegressionPersister:
    """Persist generated deterministic tests inside the candidate/project tree."""

    def persist(self, project_root: str | Path, project: str, source: str) -> dict[str, Any]:
        root=Path(project_root).resolve()
        if not root.is_dir():
            raise ValueError("project root does not exist")
        target=(root/"tests"/"krishna-generated"/f"{_safe_slug(project)}.spec.ts").resolve()
        target.relative_to(root)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(source,encoding="utf-8")
        return {"path":str(target),"sha256":sha256(source.encode()).hexdigest(),"bytes":len(source.encode()),"persisted":True}


class RegressionManifest:
    """Durable route/state coverage that is executed before fresh rediscovery."""

    @staticmethod
    def _path(url: str) -> str:
        p=urlparse(str(url or ""))
        value=p.path or "/"
        if p.query:value+="?"+p.query
        return value

    def persist(self, project_root: str | Path, project: str, graph: dict[str,Any]) -> dict[str,Any]:
        root=Path(project_root).resolve()
        target=(root/"tests"/"krishna-generated"/f"{_safe_slug(project)}.graph.json").resolve()
        target.relative_to(root);target.parent.mkdir(parents=True,exist_ok=True)
        routes=sorted({self._path(x.get("url")) for x in graph.get("nodes") or [] if x.get("url")})
        edges=[]
        for edge in graph.get("edges") or []:
            edges.append({
                "source":self._path(edge.get("source")),"target":self._path(edge.get("target")),
                "action":str(edge.get("action") or ""),"label":str(edge.get("label") or "")[:200],
                "state_id":edge.get("state_id"),
            })
        payload={"version":1,"project":project,"routes":routes,"edges":edges}
        target.write_text(json.dumps(payload,indent=2),encoding="utf-8")
        return {"path":str(target),"route_count":len(routes),"edge_count":len(edges),
                "sha256":sha256(target.read_bytes()).hexdigest(),"persisted":True}

    def load(self, project_root: str | Path, project: str) -> dict[str,Any] | None:
        root=Path(project_root).resolve()
        path=(root/"tests"/"krishna-generated"/f"{_safe_slug(project)}.graph.json").resolve()
        try:path.relative_to(root)
        except ValueError:return None
        if not path.is_file():return None
        try:
            raw=json.loads(path.read_text(encoding="utf-8"))
            return raw if isinstance(raw,dict) else None
        except Exception:
            return None


class BrowserRegressionRunner:
    """Execute persisted routes with the canonical KRISHNA browser inspector."""

    def run(self, browser, base_url: str, manifest: dict[str,Any] | None) -> dict[str,Any]:
        if not manifest:
            return {"available":False,"passed":True,"reason":"no_previous_manifest","routes":[]}
        rows=[]
        for route in manifest.get("routes") or []:
            target=urljoin(base_url,str(route))
            try:
                report=browser.inspect(target)
                rows.append({"route":route,"url":target,"passed":bool(report.get("ok")),
                             "findings":report.get("findings") or [],"layout":report.get("layout") or {}})
            except Exception as exc:
                rows.append({"route":route,"url":target,"passed":False,
                             "error":f"{type(exc).__name__}: {exc}"})
        return {"available":True,"routes":rows,"route_count":len(rows),
                "passed":bool(rows) and all(bool(x.get("passed")) for x in rows)}


class VisualBaselineStore:
    """Golden screenshot memory with optional pixel-level Pillow comparison."""

    def __init__(self, root: str | Path):
        self.root=Path(root).resolve()

    def approve(self, project: str, key: str, screenshot: str | Path) -> dict[str,Any]:
        shot=Path(screenshot).resolve()
        if not shot.is_file():raise FileNotFoundError(str(shot))
        base=self.root/_safe_slug(project)/(f"{_safe_slug(key)}.png")
        base.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(shot,base)
        return {"approved":True,"baseline":str(base),"source":str(shot),
                "sha256":sha256(shot.read_bytes()).hexdigest()}

    def compare(self, project: str, key: str, screenshot: str | Path, approve_missing: bool=False,
                max_changed_ratio: float=0.001) -> dict[str, Any]:
        shot=Path(screenshot).resolve()
        if not shot.is_file():
            return {"passed":False,"reason":"screenshot_missing","screenshot":str(shot)}
        base=self.root/_safe_slug(project)/(f"{_safe_slug(key)}.png")
        base.parent.mkdir(parents=True,exist_ok=True)
        if not base.exists():
            if approve_missing:
                shutil.copy2(shot,base)
                return {"passed":True,"created":True,"baseline":str(base),"changed_ratio":0.0}
            return {"passed":False,"reason":"baseline_missing","baseline":str(base),"candidate":str(shot)}
        if sha256(base.read_bytes()).digest()==sha256(shot.read_bytes()).digest():
            return {"passed":True,"baseline":str(base),"candidate":str(shot),"changed_ratio":0.0,"mode":"byte_identical"}
        try:
            from PIL import Image, ImageChops
            left=Image.open(base).convert("RGBA"); right=Image.open(shot).convert("RGBA")
            if left.size!=right.size:
                return {"passed":False,"baseline":str(base),"candidate":str(shot),"reason":"dimension_change",
                        "baseline_size":left.size,"candidate_size":right.size,"changed_ratio":1.0}
            diff=ImageChops.difference(left,right)
            hist=diff.convert("L").histogram()
            total=left.size[0]*left.size[1]
            unchanged=hist[0] if hist else 0
            ratio=(total-unchanged)/total if total else 1.0
            return {"passed":ratio<=float(max_changed_ratio),"baseline":str(base),"candidate":str(shot),
                    "changed_ratio":round(ratio,8),"threshold":float(max_changed_ratio),"mode":"pixel_diff"}
        except Exception as exc:
            return {"passed":False,"baseline":str(base),"candidate":str(shot),
                    "reason":"pixel_comparator_unavailable","detail":f"{type(exc).__name__}: {exc}",
                    "mode":"hash_only"}


class MutationRunner:
    """Apply reversible mutations only inside isolated candidate workspaces."""

    EXTENSIONS={".py",".js",".jsx",".ts",".tsx",".java",".html",".htm",".css",".scss"}
    EXCLUDES={".git",".venv","node_modules","dist","build",".krishna_state"}

    @staticmethod
    def _mutate(text: str, suffix: str) -> tuple[str,str] | None:
        rules=[]
        if suffix==".py":
            rules=[(" is None"," is not None"),(" == "," != "),(" True"," False"),(" False"," True")]
        elif suffix in {".html",".htm"}:
            lower=text.lower()
            if "</head>" in lower:
                idx=lower.index("</head>")
                return text[:idx]+'<style data-krishna-mutant>html body{visibility:hidden!important}</style>'+text[idx:],"hide rendered body"
            if "<body" in lower:
                idx=lower.index(">",lower.index("<body"))
                return text[:idx+1]+'<div style="position:fixed;left:-99999px">KRISHNA_MUTANT</div>'+text[idx+1:],"inject offscreen layout mutant"
            return None
        elif suffix in {".css",".scss"}:
            return "html body{visibility:hidden!important}\n"+text,"hide rendered body"
        else:
            rules=[(" === "," !== "),(" == "," != "),(" true"," false"),(" false"," true")]
        for old,new in rules:
            if old in text:
                return text.replace(old,new,1),f"{old.strip()} -> {new.strip()}"
        return None

    def run(self, candidate_root: str | Path, verify: Callable[[], dict[str, Any]], max_mutants: int=8) -> dict[str, Any]:
        root=Path(candidate_root).resolve()
        if not root.is_dir(): raise ValueError("candidate root does not exist")
        candidates=[]
        for path in root.rglob("*"):
            if len(candidates)>=max(1,min(int(max_mutants),32)): break
            if not path.is_file() or path.suffix.lower() not in self.EXTENSIONS: continue
            if any(part in self.EXCLUDES for part in path.parts): continue
            try:
                original=path.read_text(encoding="utf-8")
            except Exception: continue
            mutated=self._mutate(original,path.suffix.lower())
            if mutated: candidates.append((path,original,mutated[0],mutated[1]))
        results=[]
        for path,original,mutated,description in candidates:
            try:
                path.write_text(mutated,encoding="utf-8")
                evidence=verify()
                detected=not bool(evidence.get("verified",evidence.get("passed",False)))
                results.append({"file":str(path.relative_to(root)),"mutation":description,
                                "detected":detected,"verification":evidence})
            finally:
                path.write_text(original,encoding="utf-8")
        detected=sum(1 for x in results if x["detected"])
        total=len(results)
        return {"executed":total,"detected":detected,"score":(detected/total if total else None),
                "passed":bool(total and detected==total),"results":results,
                "rule":"mutation is performed only in candidate workspace and always restored"}


class ArtifactExecutor:
    """Clean-ish runtime retests using tools already present on the host."""

    @staticmethod
    def _cmd(args: list[str], timeout: int=120, cwd: str | Path | None=None) -> dict[str, Any]:
        started=time.perf_counter()
        try:
            p=subprocess.run(args,cwd=str(cwd) if cwd else None,capture_output=True,text=True,timeout=timeout,shell=False)
            return {"executed":True,"passed":p.returncode==0,"exit_code":p.returncode,
                    "output":((p.stdout or "")+"\n"+(p.stderr or ""))[-12000:],
                    "elapsed_ms":int((time.perf_counter()-started)*1000)}
        except FileNotFoundError as exc:
            return {"executed":False,"passed":False,"reason":"tool_unavailable","detail":str(exc)}
        except subprocess.TimeoutExpired as exc:
            return {"executed":True,"passed":False,"reason":"timeout","detail":str(exc)}

    @staticmethod
    def _health(url: str, timeout_seconds: float=2.0) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(url,timeout=timeout_seconds) as r:
                return {"reachable":True,"status":int(r.status),"passed":200<=int(r.status)<400}
        except Exception as exc:
            return {"reachable":False,"passed":False,"detail":f"{type(exc).__name__}: {exc}"}

    def exe(self, artifact: str | Path, health_url: str | None=None, startup_seconds: float=2.0,
            args: list[str] | None=None) -> dict[str, Any]:
        path=Path(artifact).resolve()
        if platform.system().lower()!="windows":
            return {"kind":"exe","executed":False,"passed":False,"reason":"windows_required"}
        if not path.is_file():
            return {"kind":"exe","executed":False,"passed":False,"reason":"artifact_missing","artifact":str(path)}
        runs=[]
        for cycle in ("launch","restart"):
            proc=None
            try:
                proc=subprocess.Popen([str(path),*(args or [])],cwd=str(path.parent),
                                      stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                time.sleep(max(0.2,float(startup_seconds)))
                alive=proc.poll() is None
                health=self._health(health_url) if health_url else {"passed":alive,"reachable":alive}
                runs.append({"cycle":cycle,"alive":alive,"health":health,"passed":alive and health["passed"]})
            except Exception as exc:
                runs.append({"cycle":cycle,"passed":False,"error":f"{type(exc).__name__}: {exc}"})
            finally:
                if proc and proc.poll() is None:
                    proc.terminate()
                    try: proc.wait(timeout=5)
                    except Exception: proc.kill()
        return {"kind":"exe","executed":True,"artifact":str(path),"runs":runs,"passed":all(x["passed"] for x in runs)}

    def apk(self, artifact: str | Path, package_id: str="com.krishna.mobile") -> dict[str, Any]:
        path=Path(artifact).resolve()
        adb=shutil.which("adb")
        if not adb:
            return {"kind":"apk","executed":False,"passed":False,"reason":"adb_unavailable"}
        if not path.is_file():
            return {"kind":"apk","executed":False,"passed":False,"reason":"artifact_missing","artifact":str(path)}
        devices=self._cmd([adb,"devices"],30)
        if not devices["passed"] or "\tdevice" not in devices.get("output",""):
            return {"kind":"apk","executed":False,"passed":False,"reason":"no_android_device","devices":devices}
        steps=[]
        steps.append({"name":"install",**self._cmd([adb,"install","-r",str(path)],180)})
        for permission in ("android.permission.CAMERA","android.permission.RECORD_AUDIO","android.permission.POST_NOTIFICATIONS"):
            grant=self._cmd([adb,"shell","pm","grant",package_id,permission],30)
            steps.append({"name":"grant_"+permission.rsplit(".",1)[-1].lower(),"permission":permission,**grant})
        permission_dump=self._cmd([adb,"shell","dumpsys","package",package_id],45)
        permission_text=permission_dump.get("output","")
        permission_verified={
            permission: (permission in permission_text and "granted=true" in permission_text[permission_text.find(permission):permission_text.find(permission)+500])
            for permission in ("android.permission.CAMERA","android.permission.RECORD_AUDIO","android.permission.POST_NOTIFICATIONS")
        }
        steps.append({"name":"launch",**self._cmd([adb,"shell","monkey","-p",package_id,"-c","android.intent.category.LAUNCHER","1"],30)})
        process=self._cmd([adb,"shell","pidof",package_id],30)
        process_ok=bool(process.get("passed") and process.get("output","").strip())
        steps.append({"name":"process_alive","executed":True,"passed":process_ok,"output":process.get("output","")})
        steps.append({"name":"background",**self._cmd([adb,"shell","input","keyevent","3"],15)})
        steps.append({"name":"foreground",**self._cmd([adb,"shell","monkey","-p",package_id,"-c","android.intent.category.LAUNCHER","1"],30)})
        steps.append({"name":"force_stop",**self._cmd([adb,"shell","am","force-stop",package_id],15)})
        steps.append({"name":"restart",**self._cmd([adb,"shell","monkey","-p",package_id,"-c","android.intent.category.LAUNCHER","1"],30)})
        restarted=self._cmd([adb,"shell","pidof",package_id],30)
        restart_process_ok=bool(restarted.get("passed") and restarted.get("output","").strip())
        steps.append({"name":"restart_process_alive","executed":True,"passed":restart_process_ok,"output":restarted.get("output","")})
        logs=self._cmd([adb,"logcat","-d","-t","500"],45)
        fatal="FATAL EXCEPTION" in logs.get("output","") and package_id in logs.get("output","")
        permissions_ok=all(permission_verified.values())
        return {"kind":"apk","executed":True,"artifact":str(path),"steps":steps,
                "permissions":permission_verified,"permissions_passed":permissions_ok,
                "fatal_in_logs":fatal,"log_tail":logs.get("output","")[-8000:],
                "passed":all(x["passed"] for x in steps) and permissions_ok and not fatal}

    def ios(self, artifact: str | Path, bundle_id: str) -> dict[str, Any]:
        path=Path(artifact).resolve()
        xcrun=shutil.which("xcrun")
        if platform.system().lower()!="darwin" or not xcrun:
            return {"kind":"ios","executed":False,"passed":False,"reason":"macos_simulator_required"}
        if not path.exists():
            return {"kind":"ios","executed":False,"passed":False,"reason":"artifact_missing","artifact":str(path)}
        steps=[
            {"name":"install",**self._cmd([xcrun,"simctl","install","booted",str(path)],120)},
            {"name":"launch",**self._cmd([xcrun,"simctl","launch","booted",bundle_id],60)},
            {"name":"terminate",**self._cmd([xcrun,"simctl","terminate","booted",bundle_id],30)},
            {"name":"restart",**self._cmd([xcrun,"simctl","launch","booted",bundle_id],60)},
        ]
        return {"kind":"ios","executed":True,"artifact":str(path),"steps":steps,
                "passed":all(x["passed"] for x in steps)}


@dataclass
class DesignCandidate:
    id: str
    label: str
    preview_url: str
    screenshot: str | None = None
    reference_url: str | None = None
    rationale: str = ""


class DesignStudio:
    """Visual-selection state: A/B/C/D are preview handles, not style names."""

    def __init__(self, root: str | Path):
        self.root=Path(root).resolve(); self.root.mkdir(parents=True,exist_ok=True)

    def save_preview(self, project: str, html: str) -> dict[str, Any]:
        token=sha256(f"{project}|{time.time_ns()}|{len(html)}".encode()).hexdigest()[:24]
        preview_root=self.root/"previews";preview_root.mkdir(parents=True,exist_ok=True)
        safe=re.sub(r"(?is)<script[^>]*>.*?</script>","",str(html or ""))
        safe=re.sub(r"(?i)\son[a-z]+\s*=\s*(['\"]).*?\1","",safe)
        safe=re.sub(r"(?i)javascript\s*:","",safe)
        csp='<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data:; font-src data:; form-action \'none\'; base-uri \'none\'">'
        if "<head" in safe.lower():
            pos=safe.lower().find(">",safe.lower().find("<head"))
            safe=safe[:pos+1]+csp+safe[pos+1:]
        else:
            safe=csp+safe
        path=preview_root/f"{token}.html";path.write_text(safe,encoding="utf-8")
        return {"token":token,"path":str(path),"preview_url":f"/api/design-studio/preview?id={token}"}

    def preview(self, token: str) -> str:
        safe=_safe_slug(token)
        path=(self.root/"previews"/f"{safe}.html").resolve()
        preview_root=(self.root/"previews").resolve()
        path.relative_to(preview_root)
        if not path.is_file():raise KeyError("design preview not found")
        return path.read_text(encoding="utf-8")

    def create(self, project: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        if not 1<=len(candidates)<=8: raise ValueError("1-8 rendered candidates required")
        sid=sha256(f"{project}|{time.time_ns()}".encode()).hexdigest()[:20]
        rows=[]
        for i,row in enumerate(candidates):
            preview=str(row.get("preview_url") or "").strip()
            if not preview: raise ValueError("each candidate requires a rendered preview_url")
            rows.append(asdict(DesignCandidate(
                id=sha256(f"{sid}|{i}|{preview}".encode()).hexdigest()[:16],
                label=chr(65+i),preview_url=preview,screenshot=row.get("screenshot"),
                reference_url=row.get("reference_url"),rationale=str(row.get("rationale") or "")[:1200],
            )))
        state={"session_id":sid,"project":project,"candidates":rows,"selected":None,"submitted":False,"created_at":time.time()}
        (self.root/f"{sid}.json").write_text(json.dumps(state,indent=2),encoding="utf-8")
        return state

    def get(self, session_id: str) -> dict[str, Any]:
        path=self.root/f"{_safe_slug(session_id)}.json"
        if not path.is_file(): raise KeyError("design session not found")
        return json.loads(path.read_text(encoding="utf-8"))

    def annotate(self, session_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
        path=self.root/f"{_safe_slug(session_id)}.json"
        state=self.get(session_id)
        state["metadata"]={**dict(state.get("metadata") or {}),**dict(metadata or {})}
        path.write_text(json.dumps(state,indent=2),encoding="utf-8")
        return state

    def submit(self, session_id: str, candidate_id: str) -> dict[str, Any]:
        path=self.root/f"{_safe_slug(session_id)}.json"
        state=self.get(session_id)
        chosen=next((x for x in state["candidates"] if x["id"]==candidate_id),None)
        if not chosen: raise KeyError("design candidate not found")
        state["selected"]=chosen;state["submitted"]=True;state["submitted_at"]=time.time()
        state["requires_implementation"]=True;state["requires_full_regression"]=True
        path.write_text(json.dumps(state,indent=2),encoding="utf-8")
        return state


class SourceMapper:
    """Map a live DOM element to likely source locations using stable visible evidence."""

    EXTENSIONS={".html",".htm",".css",".scss",".sass",".less",".js",".jsx",".ts",".tsx",".vue",".svelte",".py",".java"}
    EXCLUDES={".git",".venv","node_modules","dist","build",".krishna_state"}

    def find(self, project_root: str | Path, element: dict[str, Any], limit: int=20) -> dict[str, Any]:
        root=Path(project_root).resolve()
        if not root.is_dir(): raise ValueError("project root does not exist")
        eid=str(element.get("id") or "").strip()
        classes=[str(x).strip() for x in element.get("classes") or [] if str(x).strip()]
        name=str(element.get("name") or "").strip()
        tag=str(element.get("tag") or "").strip()
        rows=[]
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in self.EXTENSIONS: continue
            if any(part in self.EXCLUDES for part in path.parts): continue
            try: lines=path.read_text(encoding="utf-8").splitlines()
            except Exception: continue
            for no,line in enumerate(lines,1):
                score=0; reasons=[]
                if eid and (f'id="{eid}"' in line or f"id='{eid}'" in line or f"#{eid}" in line):
                    score+=8;reasons.append("id")
                for cls in classes[:6]:
                    if cls and cls in line:
                        score+=2;reasons.append("class:"+cls)
                if name and len(name)>=3 and name[:80] in line:
                    score+=5;reasons.append("visible_name")
                if tag and f"<{tag}" in line.lower():
                    score+=1;reasons.append("tag")
                if score:
                    rows.append({"path":str(path.relative_to(root)).replace("\\","/"),"line":no,
                                 "score":score,"reasons":reasons,"snippet":line.strip()[:500]})
        rows.sort(key=lambda x:(-x["score"],x["path"],x["line"]))
        return {"element":element,"candidates":rows[:max(1,min(int(limit),100))],
                "mapped":bool(rows),"root":str(root)}


class VisualCandidateEditor:
    """Apply only structured, auditable visual edits to an isolated candidate tree."""

    SAFE_CSS={
        "display","position","width","height","min-width","min-height","max-width","max-height",
        "margin","margin-top","margin-right","margin-bottom","margin-left",
        "padding","padding-top","padding-right","padding-bottom","padding-left",
        "gap","row-gap","column-gap","align-items","align-self","justify-content","justify-self",
        "grid-template-columns","grid-template-rows","grid-column","grid-row","flex","flex-direction",
        "flex-wrap","order","font-size","font-weight","line-height","text-align","border-radius",
        "box-shadow","background","background-color","color","opacity","transform","z-index",
    }

    @staticmethod
    def _stable_selector(element: dict[str, Any]) -> str:
        eid=str(element.get("id") or "").strip()
        if eid:return "#"+eid
        classes=[str(x).strip() for x in element.get("classes") or [] if str(x).strip()]
        tag=str(element.get("tag") or "").strip().lower()
        if classes:return (tag if tag else "")+"."+".".join(classes[:3])
        raise ValueError("selected element has no stable id/class selector; source-level agent patch required")

    def apply(self, candidate_root: str | Path, element: dict[str, Any], intent: dict[str, Any],
              source_map: dict[str, Any] | None=None) -> dict[str, Any]:
        root=Path(candidate_root).resolve()
        if not root.is_dir():raise ValueError("candidate root does not exist")
        action=str(intent.get("action") or "").strip().lower()
        changed=[]
        if action=="replace_text":
            old=str(element.get("name") or "").strip()
            new=str(intent.get("replacement_text") or intent.get("text") or "").strip()
            if not old or not new:raise ValueError("replace_text requires selected visible text and replacement_text")
            candidates=list((source_map or {}).get("candidates") or [])
            for row in candidates:
                path=(root/row["path"]).resolve();path.relative_to(root)
                try:text=path.read_text(encoding="utf-8")
                except Exception:continue
                if old in text:
                    path.write_text(text.replace(old,new,1),encoding="utf-8")
                    changed.append(str(path.relative_to(root)).replace("\\","/"));break
            if not changed:raise RuntimeError("could not locate selected text in candidate source")
            return {"applied":True,"action":action,"files":changed,"requires_regression":True}

        styles=dict(intent.get("style_patch") or {})
        if action in {"move","resize","restyle"}:
            if not styles:raise ValueError("structured style_patch is required for move/resize/restyle")
            safe={}
            for key,value in styles.items():
                k=str(key).strip().lower()
                if k not in self.SAFE_CSS:raise ValueError(f"unsafe or unsupported CSS property: {k}")
                v=str(value).strip()
                if not v or any(x in v.lower() for x in ("javascript:","expression(","url(data:")):
                    raise ValueError("unsafe CSS value")
                safe[k]=v
            selector=self._stable_selector(element)
            rule=selector+"{"+ ";".join(f"{k}:{v}" for k,v in safe.items())+";}\n"
            css=(root/"krishna-visual-overrides.css").resolve();css.write_text((css.read_text(encoding="utf-8") if css.exists() else "")+rule,encoding="utf-8")
            changed.append(str(css.relative_to(root)).replace("\\","/"))
            htmls=[p for p in root.rglob("index.html") if not any(part in self.EXCLUDES for part in p.parts)]
            if not htmls:
                return {"applied":False,"action":action,"files":changed,"selector":selector,
                        "reason":"override_created_but_no_index_html_to_link","requires_source_agent":True}
            html=htmls[0];text=html.read_text(encoding="utf-8")
            href=str(css.relative_to(html.parent)).replace("\\","/")
            marker='data-krishna-visual-overrides="1"'
            if marker not in text:
                link=f'<link {marker} rel="stylesheet" href="{href}">'
                text=text.replace("</head>",link+"\n</head>") if "</head>" in text else link+"\n"+text
                html.write_text(text,encoding="utf-8");changed.append(str(html.relative_to(root)).replace("\\","/"))
            return {"applied":True,"action":action,"files":changed,"selector":selector,
                    "style_patch":safe,"requires_regression":True}

        if action in {"remove","add_component"}:
            return {"applied":False,"action":action,"reason":"semantic source patch required",
                    "requires_source_agent":True,"requires_regression":True}
        raise ValueError("unsupported visual candidate edit")


class CandidateStaticServer:
    """Loopback-only static preview for isolated candidates with a safe HTML entry."""

    ENTRY_NAMES=("index.html","dashboard.html","web_validation.html")

    @classmethod
    def find_entry(cls, candidate_root: str | Path) -> Path | None:
        root=Path(candidate_root).resolve()
        direct=[root/name for name in cls.ENTRY_NAMES]
        for path in direct:
            if path.is_file():return path
        candidates=[]
        for name in cls.ENTRY_NAMES:
            for path in root.rglob(name):
                if any(part in {".git",".venv","node_modules","dist","build",".krishna_state"} for part in path.parts):
                    continue
                candidates.append(path)
        candidates.sort(key=lambda p:(cls.ENTRY_NAMES.index(p.name) if p.name in cls.ENTRY_NAMES else 99,len(p.parts),str(p)))
        return candidates[0] if candidates else None

    @contextmanager
    def serve(self, candidate_root: str | Path):
        root=Path(candidate_root).resolve()
        entry=self.find_entry(root)
        if entry is None:
            yield {"available":False,"url":None,"reason":"no_static_html_entry"}
            return
        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self,format,*args):pass
        def factory(*args,**kwargs):
            return Quiet(*args,directory=str(root),**kwargs)
        server=ThreadingHTTPServer(("127.0.0.1",0),factory)
        thread=threading.Thread(target=server.serve_forever,name="krishna-candidate-preview",daemon=True)
        thread.start()
        try:
            host,port=server.server_address
            rel=str(entry.relative_to(root)).replace("\\","/")
            yield {"available":True,"url":f"http://127.0.0.1:{port}/"+rel,"root":str(root),"entry":rel}
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)
