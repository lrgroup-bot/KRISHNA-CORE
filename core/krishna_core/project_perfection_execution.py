from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable
import json
import os
import platform
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


class VisualBaselineStore:
    """Golden screenshot memory with optional pixel-level Pillow comparison."""

    def __init__(self, root: str | Path):
        self.root=Path(root).resolve()

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

    EXTENSIONS={".py",".js",".jsx",".ts",".tsx",".java"}
    EXCLUDES={".git",".venv","node_modules","dist","build",".krishna_state"}

    @staticmethod
    def _mutate(text: str, suffix: str) -> tuple[str,str] | None:
        rules=[]
        if suffix==".py":
            rules=[(" is None"," is not None"),(" == "," != "),(" True"," False"),(" False"," True")]
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
        steps.append({"name":"launch",**self._cmd([adb,"shell","monkey","-p",package_id,"-c","android.intent.category.LAUNCHER","1"],30)})
        steps.append({"name":"background",**self._cmd([adb,"shell","input","keyevent","3"],15)})
        steps.append({"name":"foreground",**self._cmd([adb,"shell","monkey","-p",package_id,"-c","android.intent.category.LAUNCHER","1"],30)})
        steps.append({"name":"force_stop",**self._cmd([adb,"shell","am","force-stop",package_id],15)})
        steps.append({"name":"restart",**self._cmd([adb,"shell","monkey","-p",package_id,"-c","android.intent.category.LAUNCHER","1"],30)})
        logs=self._cmd([adb,"logcat","-d","-t","300"],45)
        fatal="FATAL EXCEPTION" in logs.get("output","") and package_id in logs.get("output","")
        return {"kind":"apk","executed":True,"artifact":str(path),"steps":steps,
                "fatal_in_logs":fatal,"log_tail":logs.get("output","")[-6000:],
                "passed":all(x["passed"] for x in steps) and not fatal}

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

    def submit(self, session_id: str, candidate_id: str) -> dict[str, Any]:
        path=self.root/f"{_safe_slug(session_id)}.json"
        if not path.is_file(): raise KeyError("design session not found")
        state=json.loads(path.read_text(encoding="utf-8"))
        chosen=next((x for x in state["candidates"] if x["id"]==candidate_id),None)
        if not chosen: raise KeyError("design candidate not found")
        state["selected"]=chosen;state["submitted"]=True;state["submitted_at"]=time.time()
        state["requires_implementation"]=True;state["requires_full_regression"]=True
        path.write_text(json.dumps(state,indent=2),encoding="utf-8")
        return state
