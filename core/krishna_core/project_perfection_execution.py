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
import sqlite3
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
                "role":str(edge.get("role") or "")[:80],"name":str(edge.get("name") or edge.get("label") or "")[:200],
                "selector":str(edge.get("selector") or "")[:500],"state_id":edge.get("state_id"),
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
    """Execute persisted routes and safe discovered state transitions."""

    def run(self, browser, base_url: str, manifest: dict[str,Any] | None) -> dict[str,Any]:
        if not manifest:
            return {"available":False,"passed":True,"reason":"no_previous_manifest","routes":[],"edges":[]}
        routes=[]
        for route in manifest.get("routes") or []:
            target=urljoin(base_url,str(route))
            try:
                report=browser.inspect(target)
                routes.append({"route":route,"url":target,"passed":bool(report.get("ok")),
                               "findings":report.get("findings") or [],"layout":report.get("layout") or {}})
            except Exception as exc:
                routes.append({"route":route,"url":target,"passed":False,
                               "error":f"{type(exc).__name__}: {exc}"})
        edges=[]
        for edge in manifest.get("edges") or []:
            if str(edge.get("action") or "")!="click":continue
            source=urljoin(base_url,str(edge.get("source") or "/"))
            action={"type":"click"}
            if edge.get("role"):
                action.update({"role":edge.get("role"),"name":edge.get("name") or edge.get("label") or ""})
            elif edge.get("selector"):
                action["selector"]=edge.get("selector")
            else:
                edges.append({**edge,"passed":False,"reason":"locator_missing"});continue
            try:
                report=browser.inspect(source,actions=[action])
                expected=str(edge.get("target") or "")
                actual=urlparse(str(report.get("final_url") or "")).path or "/"
                passed=bool(report.get("ok"))
                if expected and expected!=(edge.get("source") or ""):
                    passed=passed and actual==urlparse(expected).path
                expected_state=str(edge.get("state_id") or "")
                actual_state=str(report.get("state_id") or "")
                state_match=(not expected_state) or (actual_state==expected_state)
                passed=bool(passed and state_match)
                edges.append({**edge,"url":source,"passed":passed,"final_url":report.get("final_url"),
                              "expected_state_id":expected_state or None,"actual_state_id":actual_state or None,
                              "state_match":state_match,"findings":report.get("findings") or []})
            except Exception as exc:
                edges.append({**edge,"url":source,"passed":False,"error":f"{type(exc).__name__}: {exc}"})
        route_ok=bool(routes) and all(bool(x.get("passed")) for x in routes)
        edge_ok=all(bool(x.get("passed")) for x in edges) if edges else True
        return {"available":True,"routes":routes,"edges":edges,"route_count":len(routes),"edge_count":len(edges),
                "passed":bool(route_ok and edge_ok)}

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


class DatabaseChaosRunner:
    """Inject a real SQLite exclusive-lock fault into a temporary database copy."""

    def run(self, database: str | Path, lock_timeout: float=0.15) -> dict[str, Any]:
        source=Path(database).resolve()
        if not source.is_file():
            return {"applicable":True,"executed":False,"passed":False,"reason":"database_missing","database":str(source)}
        started=time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="krishna-db-chaos-") as td:
            target=Path(td)/source.name
            shutil.copy2(source,target)
            primary=sqlite3.connect(str(target),timeout=lock_timeout)
            secondary=None
            injection_observed=False
            recovery_observed=False
            injection_error=None
            try:
                primary.execute("BEGIN EXCLUSIVE")
                secondary=sqlite3.connect(str(target),timeout=lock_timeout)
                try:
                    secondary.execute("CREATE TABLE krishna_chaos_probe(id INTEGER)")
                    secondary.commit()
                except sqlite3.OperationalError as exc:
                    injection_error=str(exc)
                    injection_observed="locked" in injection_error.lower()
                primary.rollback()
                if secondary:
                    try:secondary.close()
                    except Exception:pass
                secondary=sqlite3.connect(str(target),timeout=1.0)
                secondary.execute("CREATE TABLE IF NOT EXISTS krishna_chaos_probe(id INTEGER)")
                secondary.commit()
                recovery_observed=True
            finally:
                try:primary.close()
                except Exception:pass
                if secondary:
                    try:secondary.close()
                    except Exception:pass
            return {
                "applicable":True,"executed":True,"source_database":str(source),
                "temporary_database":str(target),"fault":"sqlite_exclusive_lock",
                "injection_observed":injection_observed,"injection_error":injection_error,
                "recovery_observed":recovery_observed,
                "passed":bool(injection_observed and recovery_observed),
                "elapsed_ms":int((time.perf_counter()-started)*1000),
                "safety":"fault injected only into an isolated temporary database copy",
            }


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
    def _terminate_process_tree(proc) -> dict[str, Any]:
        if proc is None:
            return {"passed":True,"reason":"no_process"}
        pid=getattr(proc,"pid",None)
        if platform.system().lower()=="windows" and pid:
            try:
                p=subprocess.run(["taskkill","/PID",str(pid),"/T","/F"],capture_output=True,text=True,timeout=15,shell=False)
                try:proc.wait(timeout=5)
                except Exception:pass
                time.sleep(0.25)
                return {"passed":p.returncode==0 or proc.poll() is not None,"pid":pid,
                        "output":((p.stdout or "")+"\n"+(p.stderr or ""))[-4000:]}
            except Exception as exc:
                return {"passed":False,"pid":pid,"error":f"{type(exc).__name__}: {exc}"}
        try:
            if proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=5)
                except Exception:
                    proc.kill();proc.wait(timeout=5)
            return {"passed":True,"pid":pid}
        except Exception as exc:
            return {"passed":False,"pid":pid,"error":f"{type(exc).__name__}: {exc}"}

    @staticmethod
    def _cleanup_sandbox(path: str | Path, attempts: int=20, delay_seconds: float=0.25) -> dict[str, Any]:
        """Remove a clean-install sandbox after Windows releases executable handles.

        Windows may keep an image section briefly after taskkill/proc.wait succeeds.
        That transient lock must not turn a successful launch/restart verification into
        an unhandled TemporaryDirectory cleanup exception.
        """
        root=Path(path)
        last_error=None
        for attempt in range(1,max(1,int(attempts))+1):
            if not root.exists():
                return {"passed":True,"attempts":attempt-1}
            try:
                shutil.rmtree(root)
                return {"passed":True,"attempts":attempt}
            except (PermissionError,OSError) as exc:
                last_error=f"{type(exc).__name__}: {exc}"
                if attempt<max(1,int(attempts)) and delay_seconds>0:
                    time.sleep(float(delay_seconds))
        return {"passed":not root.exists(),"attempts":max(1,int(attempts)),
                "error":last_error,"path":str(root)}

    def _wait_android_ready(self, adb: str, attempts: int=60,
                            delay_seconds: float=1.0) -> dict[str, Any]:
        """Wait for ADB transport and core Android framework services before app operations."""
        last={"executed":True,"passed":False,"state":"","boot":"","package_service":"","activity_service":""}
        for attempt in range(1,max(1,int(attempts))+1):
            state=self._cmd([adb,"get-state"],30)
            state_text=state.get("output","").strip()
            boot={"passed":False,"output":""}
            package_service={"passed":False,"output":""}
            activity_service={"passed":False,"output":""}
            if state.get("passed") and state_text=="device":
                boot=self._cmd([adb,"shell","getprop","sys.boot_completed"],30)
                package_service=self._cmd([adb,"shell","service","check","package"],30)
                activity_service=self._cmd([adb,"shell","service","check","activity"],30)
                boot_text=boot.get("output","").strip()
                package_text=package_service.get("output","").lower()
                activity_text=activity_service.get("output","").lower()
                if (boot.get("passed") and boot_text=="1" and
                        package_service.get("passed") and "found" in package_text and "not found" not in package_text and
                        activity_service.get("passed") and "found" in activity_text and "not found" not in activity_text):
                    return {"executed":True,"passed":True,"attempts":attempt,"state":state_text,
                            "boot":boot_text,"package_service":package_service.get("output","")[-1000:],
                            "activity_service":activity_service.get("output","")[-1000:]}
            last={"executed":True,"passed":False,"attempts":attempt,"state":state_text,
                  "boot":boot.get("output","").strip(),
                  "package_service":package_service.get("output","")[-1000:],
                  "activity_service":activity_service.get("output","")[-1000:]}
            if attempt<max(1,int(attempts)) and delay_seconds>0:
                time.sleep(float(delay_seconds))
        return last

    def _wait_android_process(self, adb: str, package_id: str, attempts: int=15,
                              delay_seconds: float=1.0) -> dict[str, Any]:
        """Wait for Android to publish the app PID after an asynchronous launcher event."""
        last={"executed":True,"passed":False,"output":""}
        for attempt in range(1,max(1,int(attempts))+1):
            last=self._cmd([adb,"shell","pidof",package_id],30)
            output=last.get("output","").strip()
            if last.get("passed") and output:
                return {"executed":True,"passed":True,"output":last.get("output",""),
                        "attempts":attempt}
            if attempt<max(1,int(attempts)) and delay_seconds>0:
                time.sleep(float(delay_seconds))
        return {"executed":True,"passed":False,"output":last.get("output",""),
                "attempts":max(1,int(attempts))}

    def _wait_android_foreground(self, adb: str, package_id: str, attempts: int=15,
                                 delay_seconds: float=1.0) -> dict[str, Any]:
        """Wait until Android reports this package as the top activity."""
        last={"executed":True,"passed":False,"output":""}
        for attempt in range(1,max(1,int(attempts))+1):
            last=self._cmd([adb,"shell","dumpsys","activity","top"],30)
            output=last.get("output","")
            if last.get("passed") and package_id in output:
                return {"executed":True,"passed":True,"output":output[-4000:],
                        "attempts":attempt}
            if attempt<max(1,int(attempts)) and delay_seconds>0:
                time.sleep(float(delay_seconds))
        return {"executed":True,"passed":False,"output":last.get("output","")[-4000:],
                "attempts":max(1,int(attempts))}

    def _launch_android_app(self, adb: str, package_id: str) -> dict[str, Any]:
        """Trigger the launcher and verify the resulting process + foreground state."""
        command=self._cmd([adb,"shell","monkey","-p",package_id,"-c",
                           "android.intent.category.LAUNCHER","1"],60)
        process=self._wait_android_process(adb,package_id)
        foreground=self._wait_android_foreground(adb,package_id)
        return {
            "executed":bool(command.get("executed",True)),
            "passed":bool(process.get("passed") and foreground.get("passed")),
            "command_passed":bool(command.get("passed")),
            "command":command,
            "process":process,
            "foreground":foreground,
        }

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
        artifact_hash=sha256(path.read_bytes()).hexdigest()
        runs=[]
        td=tempfile.mkdtemp(prefix="krishna-exe-clean-install-")
        sandbox=Path(td).resolve();staged=sandbox/path.name
        staged_hash=None
        cleanup={"passed":False,"reason":"not_attempted"}
        try:
            shutil.copy2(path,staged)
            for cycle in ("launch","restart"):
                proc=None
                try:
                    proc=subprocess.Popen([str(staged),*(args or [])],cwd=str(sandbox),
                                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                    time.sleep(max(0.2,float(startup_seconds)))
                    alive=proc.poll() is None
                    health=self._health(health_url) if health_url else {"passed":alive,"reachable":alive}
                    runs.append({"cycle":cycle,"alive":alive,"health":health,"passed":alive and health["passed"]})
                except Exception as exc:
                    runs.append({"cycle":cycle,"passed":False,"error":f"{type(exc).__name__}: {exc}"})
                finally:
                    termination=self._terminate_process_tree(proc)
                    if runs:
                        runs[-1]["termination"]=termination
                        runs[-1]["passed"]=bool(runs[-1].get("passed") and termination.get("passed"))
            staged_hash=sha256(staged.read_bytes()).hexdigest() if staged.is_file() else None
        finally:
            cleanup=self._cleanup_sandbox(sandbox)
        functional_pass=bool(staged_hash==artifact_hash and all(x["passed"] for x in runs))
        return {"kind":"exe","executed":True,"artifact":str(path),"artifact_sha256":artifact_hash,
                "clean_install":True,"sandbox_copy_verified":staged_hash==artifact_hash,
                "sandbox_cleanup":cleanup,"runs":runs,
                "passed":functional_pass,
                "cleanup_warning":None if cleanup.get("passed") else "temporary Windows executable remained locked after bounded cleanup retries"}

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
        readiness=self._wait_android_ready(adb)
        if not readiness.get("passed"):
            return {"kind":"apk","executed":False,"passed":False,"reason":"android_not_ready",
                    "devices":devices,"readiness":readiness}
        steps=[{"name":"android_ready",**readiness}]
        installed_probe=self._cmd([adb,"shell","pm","path",package_id],30)
        was_installed=bool(installed_probe.get("passed") and "package:" in installed_probe.get("output",""))
        if was_installed:
            uninstall=self._cmd([adb,"uninstall",package_id],60)
            uninstall_ok=bool(uninstall.get("passed"))
        else:
            uninstall={"executed":True,"passed":True,"reason":"package_not_installed","output":installed_probe.get("output","")}
            uninstall_ok=True
        steps.append({"name":"clean_uninstall","was_installed":was_installed,
                      "executed":uninstall.get("executed",False),"passed":uninstall_ok,
                      "output":uninstall.get("output",""),"reason":uninstall.get("reason")})
        steps.append({"name":"install",**self._cmd([adb,"install",str(path)],180)})
        for permission in ("android.permission.CAMERA","android.permission.RECORD_AUDIO","android.permission.POST_NOTIFICATIONS"):
            grant=self._cmd([adb,"shell","pm","grant",package_id,permission],30)
            steps.append({"name":"grant_"+permission.rsplit(".",1)[-1].lower(),"permission":permission,**grant})
        permission_dump=self._cmd([adb,"shell","dumpsys","package",package_id],45)
        permission_text=permission_dump.get("output","")
        permission_verified={}
        for permission in ("android.permission.CAMERA","android.permission.RECORD_AUDIO","android.permission.POST_NOTIFICATIONS"):
            # dumpsys can mention a permission first in requested/install sections and
            # only later in "runtime permissions". Parse every exact permission entry
            # rather than slicing from the first occurrence, which can create a false
            # negative even after `pm grant` succeeds.
            matches=re.findall(
                rf"(?m)^\s*{re.escape(permission)}\s*:\s*granted=(true|false)\b",
                permission_text,
            )
            permission_verified[permission]=bool(matches and matches[-1].lower()=="true")
        launch=self._launch_android_app(adb,package_id)
        steps.append({"name":"launch",**launch})
        steps.append({"name":"process_alive",**launch["process"]})
        steps.append({"name":"background",**self._cmd([adb,"shell","input","keyevent","3"],15)})
        foreground=self._launch_android_app(adb,package_id)
        steps.append({"name":"foreground",**foreground})
        steps.append({"name":"force_stop",**self._cmd([adb,"shell","am","force-stop",package_id],15)})
        restart=self._launch_android_app(adb,package_id)
        steps.append({"name":"restart",**restart})
        steps.append({"name":"restart_process_alive",**restart["process"]})
        logs=self._cmd([adb,"logcat","-d","-t","500"],45)
        fatal="FATAL EXCEPTION" in logs.get("output","") and package_id in logs.get("output","")
        permissions_ok=all(permission_verified.values())
        return {"kind":"apk","executed":True,"artifact":str(path),"steps":steps,
                "permissions":permission_verified,"permissions_passed":permissions_ok,
                "fatal_in_logs":fatal,"log_tail":logs.get("output","")[-8000:],
                "clean_install":True,"passed":all(x["passed"] for x in steps) and permissions_ok and not fatal}

    def ios(self, artifact: str | Path, bundle_id: str) -> dict[str, Any]:
        path=Path(artifact).resolve()
        xcrun=shutil.which("xcrun")
        if platform.system().lower()!="darwin" or not xcrun:
            return {"kind":"ios","executed":False,"passed":False,"reason":"macos_simulator_required"}
        if not path.exists():
            return {"kind":"ios","executed":False,"passed":False,"reason":"artifact_missing","artifact":str(path)}
        if not str(bundle_id or "").strip():
            return {"kind":"ios","executed":False,"passed":False,"reason":"bundle_id_required"}
        installed_probe=self._cmd([xcrun,"simctl","get_app_container","booted",bundle_id],30)
        was_installed=bool(installed_probe.get("passed") and installed_probe.get("output","").strip())
        if was_installed:
            clean=self._cmd([xcrun,"simctl","uninstall","booted",bundle_id],60)
            clean_ok=bool(clean.get("passed"))
        else:
            clean={"executed":True,"passed":True,"reason":"bundle_not_installed","output":installed_probe.get("output","")}
            clean_ok=True
        steps=[
            {"name":"clean_uninstall","was_installed":was_installed,
             "executed":clean.get("executed",False),"passed":clean_ok,
             "output":clean.get("output",""),"reason":clean.get("reason")},
            {"name":"install",**self._cmd([xcrun,"simctl","install","booted",str(path)],120)},
            {"name":"launch",**self._cmd([xcrun,"simctl","launch","booted",bundle_id],60)},
            {"name":"terminate",**self._cmd([xcrun,"simctl","terminate","booted",bundle_id],30)},
            {"name":"restart",**self._cmd([xcrun,"simctl","launch","booted",bundle_id],60)},
        ]
        return {"kind":"ios","executed":True,"artifact":str(path),"steps":steps,
                "clean_install":True,"passed":all(x["passed"] for x in steps)}

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
