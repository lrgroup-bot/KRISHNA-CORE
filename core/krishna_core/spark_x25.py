from __future__ import annotations

"""Spark-X2.5 candidate integration for KRISHNA.

This module intentionally does not auto-download or auto-promote models. Spark enters
through Model Scout, is benchmarked against existing local models, and may only become
routing-enabled after explicit review + verification evidence.
"""

from contextlib import nullcontext
from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import json
import os
import re
import tempfile
import time
import urllib.request

from .long_context import LongContextLab
from .model_scout import ModelCandidate


@dataclass(frozen=True)
class SparkSpec:
    key: str
    model_id: str
    params_b: float
    intended_role: str
    context_profiles: tuple[int, ...]
    official_context_max: int = 1_048_576

    def as_dict(self):
        return asdict(self)


class SparkX25Manager:
    VERSION="spark-x2.5-integration-v1"
    OFFICIAL_REPO="https://github.com/XHToken/Spark-X2.5"
    LICENSE="Apache-2.0"
    MIN_OLLAMA=(0,34,1)
    DEFAULT_WINDOWS_MODEL_ROOT=r"E:\Krishna-The GOD\ollama-models"
    VERIFIED_RUNTIMES=("ollama","llama.cpp","lm-studio","mlx","vllm","sglang")
    MOBILE_RUNTIME_CANDIDATES=("llama.cpp-android","native-ndk-jni")
    UNVERIFIED_RUNTIMES=("litert","litert-lm")
    STAGES=("DISCOVERED","DOWNLOADED","BENCHMARKED","CANDIDATE","REVIEWED","VERIFIED","ROUTING_ENABLED")
    SPECS={
        "spark-x2.5-1.7b":SparkSpec(
            "spark-x2.5-1.7b","SparkLLM/Spark-X2.5-1.7B",1.7,
            "LOCAL_MOBILE_REASONER",(4096,8192,16384,32768),
        ),
        "spark-x2.5-4b":SparkSpec(
            "spark-x2.5-4b","SparkLLM/Spark-X2.5-4B",4.0,
            "LOCAL_GENERAL_AGENT",(8192,16384,32768,65536,131072),
        ),
    }

    def __init__(self,state_root,model_scout,resource_governor=None,router=None):
        self.root=Path(state_root)
        self.root.mkdir(parents=True,exist_ok=True)
        self.benchmarks=self.root/"model_benchmarks"
        self.benchmarks.mkdir(exist_ok=True)
        self.lifecycle_path=self.root/"lifecycle.json"
        self.model_scout=model_scout
        self.resource_governor=resource_governor
        self.router=router
        self._ensure_lifecycle()

    @classmethod
    def _default_state(cls):
        return {
            "stage":"DISCOVERED","routing_enabled":False,
            "reviewed":False,"verified":False,
        }

    @classmethod
    def _advance_stage_state(cls,state,target):
        target=str(target or "").strip().upper()
        if target not in cls.STAGES:raise ValueError("invalid Spark lifecycle stage: "+target)
        current=str(state.get("stage") or "DISCOVERED").strip().upper()
        if current not in cls.STAGES:current="DISCOVERED"
        if cls.STAGES.index(target)>cls.STAGES.index(current):
            state["stage"]=target
        else:
            state["stage"]=current
        return state

    @staticmethod
    def _installed(status,model_id):
        wanted=str(model_id or "").strip().lower()
        installed={str(x or "").strip().lower() for x in (status.get("installed_models") or [])}
        return wanted in installed or (wanted+":latest") in installed

    def _ensure_lifecycle(self):
        if self.lifecycle_path.exists():return
        self._save_lifecycle({
            "schema":1,"version":self.VERSION,
            "models":{k:self._default_state() for k in self.SPECS},
            "updated_at":time.time(),
        })

    def _load_lifecycle(self):
        if not self.lifecycle_path.exists():
            return {
                "schema":1,"version":self.VERSION,
                "models":{k:self._default_state() for k in self.SPECS},
            }
        try:
            data=json.loads(self.lifecycle_path.read_text(encoding="utf-8"))
            if not isinstance(data,dict):raise ValueError("lifecycle root must be an object")
            schema=data.get("schema",1)
            version=data.get("version",self.VERSION)
            if schema!=1:raise ValueError(f"unsupported lifecycle schema: {schema!r}")
            if version!=self.VERSION:raise ValueError(f"unsupported lifecycle version: {version!r}")
            models=data.get("models",{})
            if not isinstance(models,dict):raise ValueError("lifecycle models must be an object")
            data["schema"]=1;data["version"]=self.VERSION;data["models"]=models
            for key in self.SPECS:
                state=data["models"].setdefault(key,self._default_state())
                for field,value in self._default_state().items():state.setdefault(field,value)
            return data
        except Exception as exc:
            raise RuntimeError(
                "Spark lifecycle state is unreadable; refusing overwrite: "
                + f"{type(exc).__name__}: {exc}"
            ) from exc

    def _save_lifecycle(self,data):
        self.lifecycle_path.parent.mkdir(parents=True,exist_ok=True)
        data["updated_at"]=time.time()
        fd,tmp=tempfile.mkstemp(prefix="spark-x25-",suffix=".json",dir=str(self.lifecycle_path.parent))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as h:json.dump(data,h,indent=2,ensure_ascii=False)
            os.replace(tmp,self.lifecycle_path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

    @staticmethod
    def _parse_version(text):
        m=re.search(r"(\d+)\.(\d+)\.(\d+)",str(text or ""))
        return tuple(int(x) for x in m.groups()) if m else (0,0,0)

    def _probe_json(self,path,timeout=3):
        base=os.getenv("KRISHNA_OLLAMA_URL","http://127.0.0.1:11434").rstrip("/")
        try:
            with urllib.request.urlopen(base+path,timeout=timeout) as r:return json.loads(r.read().decode())
        except Exception as exc:return {"error":f"{type(exc).__name__}: {exc}"}

    def ollama_status(self):
        version=self._probe_json("/api/version")
        tags=self._probe_json("/api/tags")
        raw_version=version.get("version","") if isinstance(version,dict) else ""
        parsed=self._parse_version(raw_version)
        names=[]
        if isinstance(tags,dict):
            for row in tags.get("models") or []:
                name=str(row.get("name") or row.get("model") or "").strip()
                if name:names.append(name)
        root=str(os.getenv("OLLAMA_MODELS") or "")
        e_drive_ok=True
        if os.name=="nt":
            e_drive_ok=bool(root and Path(root).drive.upper()=="E:")
        version_error=version.get("error") if isinstance(version,dict) else "invalid Ollama version response"
        tags_error=tags.get("error") if isinstance(tags,dict) else "invalid Ollama tags response"
        return {
            "available":not version_error and not tags_error,
            "version":raw_version,
            "minimum_version":".".join(map(str,self.MIN_OLLAMA)),
            "architecture_supported":parsed>=self.MIN_OLLAMA,
            "installed_models":sorted(names),
            "model_root":root,
            "windows_e_drive_policy_ok":e_drive_ok,
            "default_windows_model_root":self.DEFAULT_WINDOWS_MODEL_ROOT,
            "error":version_error or tags_error,
        }

    def candidate_metadata(self,key):
        spec=self.SPECS[key]
        return {
            **spec.as_dict(),
            "family":"Spark-X2.5",
            "provider":"local",
            "official_source":self.OFFICIAL_REPO,
            "license":self.LICENSE,
            "vision":False,
            "audio":False,
            "tool_calling":{"claimed":True,"verified":False},
            "long_context":{"claimed":True,"max_claimed":spec.official_context_max,"verified":False},
            "multilingual":{"claimed_over_200_languages":True,"verified_for_odia":False,"verified_for_hindi":False},
            "cloud":False,
            "privacy":"local",
            "runtime_support":{
                "officially_documented":list(self.VERIFIED_RUNTIMES),
                "verified_in_krishna":[],
                "mobile_candidates":list(self.MOBILE_RUNTIME_CANDIDATES),
                "not_verified_upstream":list(self.UNVERIFIED_RUNTIMES),
            },
            "authority":"worker-model-only",
            "action_path":"Shared Action Bus -> Permission Runtime -> KABACH -> executor -> Sudarshan verifier",
        }

    def discover(self):
        """Discover Spark candidates without downgrading prior benchmark/promotion state."""
        lifecycle=self._load_lifecycle()
        ollama=self.ollama_status()
        rows={}
        for key,spec in self.SPECS.items():
            state=lifecycle.setdefault("models",{}).setdefault(key,self._default_state())
            for field,value in self._default_state().items():state.setdefault(field,value)
            existing=dict(self.model_scout.rows.get(spec.model_id) or {})
            if existing:
                row=existing
            else:
                row=self.model_scout.evaluate(ModelCandidate(
                    model_id=spec.model_id,
                    source="local",
                    task=spec.intended_role.lower(),
                    license=self.LICENSE,
                    local_capable=True,
                    quality=0.0,
                    benchmark_ref="",
                    notes="Spark-X2.5 official candidate; benchmark required before promotion",
                ))
            if self._installed(ollama,spec.model_id):
                self._advance_stage_state(state,"DOWNLOADED")
            if row.get("benchmarked"):
                self._advance_stage_state(state,"BENCHMARKED")
                if row.get("benchmark_ref"):state.setdefault("benchmark_ref",row.get("benchmark_ref"))
            if row.get("accepted"):self._advance_stage_state(state,"CANDIDATE")
            if row.get("reviewed"):
                state["reviewed"]=True
                if row.get("review_ref"):state["review_ref"]=row.get("review_ref")
                self._advance_stage_state(state,"REVIEWED")
            if row.get("verified"):
                state["verified"]=True
                if row.get("verification_ref"):state["verification_ref"]=row.get("verification_ref")
                self._advance_stage_state(state,"VERIFIED")
            if row.get("routing_enabled"):
                state.update({"reviewed":True,"verified":True,"routing_enabled":True})
                self._advance_stage_state(state,"ROUTING_ENABLED")
            rows[key]={"spec":self.candidate_metadata(key),"scout":dict(row),"lifecycle":dict(state)}
        self._save_lifecycle(lifecycle)
        return {"family":"Spark-X2.5","candidates":rows,"routing_changed":False,"ollama":ollama}

    def preflight(self,key):
        spec=self.SPECS[key]
        status=self.ollama_status()
        lifecycle=self._load_lifecycle()
        state=lifecycle.setdefault("models",{}).setdefault(key,self._default_state())
        installed=self._installed(status,spec.model_id)
        if installed:
            self._advance_stage_state(state,"DOWNLOADED")
            self._save_lifecycle(lifecycle)
        return {
            "model_key":key,
            "model":spec.model_id,
            "ollama":status,
            "installed":installed,
            "ready_for_benchmark":bool(
                status.get("available")
                and status.get("architecture_supported")
                and status.get("windows_e_drive_policy_ok")
                and installed
            ),
            "no_download_performed":True,
            "lifecycle":dict(state),
        }

    def install_plan(self,key):
        spec=self.SPECS[key]
        status=self.ollama_status()
        return {
            "model":spec.model_id,
            "runtime":"ollama",
            "automatic_download":False,
            "approval_required":True,
            "storage_policy":{
                "do_not_use_c_drive":True,
                "OLLAMA_MODELS":status.get("model_root") or self.DEFAULT_WINDOWS_MODEL_ROOT,
            },
            "preconditions":{
                "ollama_minimum":"0.34.1",
                "ollama_architecture_supported":bool(status.get("architecture_supported")),
                "windows_e_drive_policy_ok":bool(status.get("windows_e_drive_policy_ok")),
            },
            "command":f"ollama run {spec.model_id}",
            "note":"Execute only after explicit model-install approval; discovery alone never downloads weights.",
        }

    def _ollama_generate(self,model,prompt,num_ctx=4096,timeout=180):
        base=os.getenv("KRISHNA_OLLAMA_URL","http://127.0.0.1:11434").rstrip("/")
        body=json.dumps({
            "model":model,"prompt":prompt,"stream":False,
            "options":{"temperature":0,"num_ctx":int(num_ctx)},
        }).encode()
        req=urllib.request.Request(base+"/api/generate",data=body,headers={"Content-Type":"application/json"})
        started=time.perf_counter()
        with urllib.request.urlopen(req,timeout=timeout) as r:data=json.loads(r.read().decode())
        elapsed=time.perf_counter()-started
        eval_count=int(data.get("eval_count") or 0)
        eval_duration=int(data.get("eval_duration") or 0)
        return {
            "text":str(data.get("response") or ""),
            "elapsed_s":elapsed,
            "eval_count":eval_count,
            "eval_duration_ns":eval_duration,
            "tokens_per_s":(eval_count/(eval_duration/1e9)) if eval_count and eval_duration else 0.0,
            "prompt_eval_count":int(data.get("prompt_eval_count") or 0),
            "prompt_eval_duration_ns":int(data.get("prompt_eval_duration") or 0),
            "load_duration_ns":int(data.get("load_duration") or 0),
            "total_duration_ns":int(data.get("total_duration") or 0),
            "num_ctx":int(num_ctx),
        }

    @staticmethod
    def _json_score(text,expected_action):
        try:
            obj=json.loads(str(text).strip())
            return 1.0 if obj.get("action")==expected_action and isinstance(obj.get("arguments"),dict) else 0.0
        except Exception:return 0.0

    def benchmark(self,key,runner=None,device=None,quantization="unknown",full=False):
        if runner is None:
            preflight=self.preflight(key)
            if not preflight["ready_for_benchmark"]:
                raise RuntimeError("Spark benchmark preflight failed; verify Ollama version, E-drive model storage, and installed model")
        guard=self.resource_governor.job(timeout=0) if self.resource_governor else nullcontext()
        with guard:
            return self._benchmark_impl(key,runner=runner,device=device,quantization=quantization,full=full)

    def _benchmark_impl(self,key,runner=None,device=None,quantization="unknown",full=False):
        spec=self.SPECS[key]
        runner=runner or (lambda prompt,ctx:self._ollama_generate(spec.model_id,prompt,ctx))
        tool_cases=[
            ("Return JSON only: choose action project.inspect with arguments {\"project\":\"LRS Motors\"}.","project.inspect"),
            ("Return JSON only: unavailable tools must stop. Available actions: browser.open. User asks delete disk. Return action STOP with arguments {}.","STOP"),
        ]
        tool_rows=[]
        latencies=[];tps=[]
        for prompt,expected in tool_cases:
            out=runner(prompt,4096)
            tool_rows.append({"expected":expected,"score":self._json_score(out.get("text",""),expected),"text":out.get("text","")[:500]})
            latencies.append(float(out.get("elapsed_s") or 0));tps.append(float(out.get("tokens_per_s") or 0))

        language_prompts={
            "english":"Reply briefly in English: explain what an electric motor does.",
            "hindi":"हिंदी में संक्षेप में बताइए कि इलेक्ट्रिक मोटर क्या करती है।",
            "odia":"ଓଡ଼ିଆରେ ସଂକ୍ଷେପରେ କହନ୍ତୁ ଇଲେକ୍ଟ୍ରିକ୍ ମୋଟର କଣ କରେ।",
            "odia_transliterated":"Odia re sankhepare kuha electric motor kana kare.",
            "hindi_transliterated":"Hindi me sankshipt batao electric motor kya karti hai.",
            "noisy_transcript":"plz chk moter vibraion n tell nxt safe obsrvation",
        }
        languages={}
        for name,prompt in language_prompts.items():
            out=runner(prompt,4096)
            languages[name]={"nonempty":bool(str(out.get("text") or "").strip()),"text":str(out.get("text") or "")[:1000],"review_required":True}
            latencies.append(float(out.get("elapsed_s") or 0));tps.append(float(out.get("tokens_per_s") or 0))

        context_sizes=spec.context_profiles if full else spec.context_profiles[:2]
        lab=LongContextLab()
        def lc_runner(prompt):
            # Use the requested benchmark context size as the Ollama num_ctx cap,
            # but never silently jump to the vendor-claimed 1M context.
            ctx=max(4096,min(max(context_sizes),len(prompt)//2+2048))
            return runner(prompt,ctx).get("text","")
        long_context=lab.needle_matrix(lc_runner,context_sizes=context_sizes,positions=(0.0,0.25,0.5,0.75,1.0))

        tool_score=sum(x["score"] for x in tool_rows)/max(1,len(tool_rows))
        mechanical_score=(tool_score*0.45)+(float(long_context.get("pass_rate") or 0)*0.45)+(0.10 if all(x["nonempty"] for x in languages.values()) else 0.0)
        report={
            "schema":"krishna.spark-x25-benchmark.v1",
            "family":"Spark-X2.5","model_key":key,"model":spec.model_id,
            "official_source":self.OFFICIAL_REPO,"license":self.LICENSE,
            "date":time.time(),"device":device or os.getenv("COMPUTERNAME") or os.getenv("HOSTNAME") or "unknown",
            "runtime":"ollama","quantization":quantization,
            "context_profiles_tested":list(context_sizes),
            "vendor_context_claim":spec.official_context_max,
            "vendor_claim_not_used_as_evidence":True,
            "tool_json":{"score":tool_score,"cases":tool_rows},
            "languages":languages,
            "long_context":long_context,
            "performance":{
                "mean_elapsed_s":sum(latencies)/max(1,len(latencies)),
                "mean_tokens_per_s":sum(tps)/max(1,len(tps)),
            },
            "mechanical_score":round(mechanical_score,6),
            "coding_review_required":True,
            "agent_review_required":True,
            "multilingual_quality_review_required":True,
            "promotion_ready":False,
            "review_status":"BENCHMARKED_NOT_REVIEWED",
        }
        digest=hashlib.sha256(json.dumps(report,sort_keys=True,default=str).encode()).hexdigest()
        report["benchmark_id"]="spark-"+digest[:20]
        path=self.benchmarks/(key+".json")
        path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
        lifecycle=self._load_lifecycle()
        state=lifecycle.setdefault("models",{}).setdefault(key,self._default_state())
        state["benchmark_ref"]=report["benchmark_id"]
        self._advance_stage_state(state,"BENCHMARKED")
        self._save_lifecycle(lifecycle)
        return report

    def review(self,key,*,coding_score,agent_score,multilingual_score,review_ref,
               ram_bytes=0,vram_bytes=0,latency_ms=0,minimum_score=0.55):
        path=self.benchmarks/(key+".json")
        if not path.exists():raise RuntimeError("Spark benchmark must run before review")
        report=json.loads(path.read_text(encoding="utf-8"))
        review_ref=str(review_ref or "").strip()
        if not review_ref:
            raise ValueError("review_ref is required")
        scores=[float(coding_score),float(agent_score),float(multilingual_score)]
        if any(x<0 or x>1 for x in scores):raise ValueError("review scores must be between 0 and 1")
        quality=(float(report.get("mechanical_score") or 0)*0.4)+(scores[0]*0.25)+(scores[1]*0.20)+(scores[2]*0.15)
        spec=self.SPECS[key]
        scout=self.model_scout.evaluate(ModelCandidate(
            model_id=spec.model_id,source="local",task=spec.intended_role.lower(),license=self.LICENSE,
            local_capable=True,quality=quality,latency_ms=float(latency_ms),ram_bytes=int(ram_bytes),
            vram_bytes=int(vram_bytes),benchmark_ref=str(report["benchmark_id"]),
            notes="Spark-X2.5 reviewed benchmark candidate",
        ),min_score=minimum_score)
        lifecycle=self._load_lifecycle()
        state=lifecycle.setdefault("models",{}).setdefault(key,self._default_state())
        if scout.get("accepted"):
            self._advance_stage_state(state,"CANDIDATE")
            state["reviewed"]=True
            self._advance_stage_state(state,"REVIEWED")
        state.update({
            "review_ref":review_ref,
            "quality":quality,
        })
        state.pop("verification_ref",None)
        report.update({
            "coding_score":scores[0],"agent_score":scores[1],"multilingual_score":scores[2],
            "review_ref":review_ref,
            "quality":quality,
            "candidate_accepted":bool(scout.get("accepted")),
            "promotion_ready":False,
            "verification_status":"NOT_VERIFIED",
            "review_status":"REVIEWED_CANDIDATE" if scout.get("accepted") else "REVIEWED_HOLD",
        })
        report.pop("verification_ref",None)
        path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
        self._save_lifecycle(lifecycle)
        return {"benchmark":report,"scout":scout,"lifecycle":dict(state)}

    def verify(self,key,*,review_ref,verification_ref):
        lifecycle=self._load_lifecycle()
        state=lifecycle.setdefault("models",{}).setdefault(key,self._default_state())
        if not state.get("reviewed"):
            raise RuntimeError("Spark candidate must be reviewed before verification")
        review_ref=str(review_ref or "").strip()
        verification_ref=str(verification_ref or "").strip()
        if not review_ref or not verification_ref:
            raise ValueError("review_ref and verification_ref are required")
        if state.get("review_ref") and str(state.get("review_ref"))!=review_ref:
            raise ValueError("review_ref does not match reviewed candidate")
        spec=self.SPECS[key]
        scout=dict(self.model_scout.rows.get(spec.model_id) or {})
        if not scout.get("accepted") or not scout.get("benchmarked"):
            raise RuntimeError("Spark candidate is no longer an accepted benchmark candidate")
        state.update({"reviewed":True,"verified":True,"review_ref":review_ref,"verification_ref":verification_ref})
        self._advance_stage_state(state,"VERIFIED")
        path=self.benchmarks/(key+".json")
        report=json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        report.update({
            "review_ref":review_ref,
            "verification_ref":verification_ref,
            "verification_status":"VERIFIED",
            "promotion_ready":True,
        })
        if report:path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
        self._save_lifecycle(lifecycle)
        return {"model":spec.model_id,"benchmark":report,"lifecycle":dict(state)}

    def enable_routing(self,key,*,review_ref,verification_ref):
        spec=self.SPECS[key]
        lifecycle=self._load_lifecycle()
        state=lifecycle.setdefault("models",{}).setdefault(key,self._default_state())
        review_ref=str(review_ref or "").strip();verification_ref=str(verification_ref or "").strip()
        if not state.get("reviewed") or not state.get("verified"):
            raise RuntimeError("Spark candidate must be reviewed and verified before routing can be enabled")
        if str(state.get("review_ref") or "")!=review_ref or str(state.get("verification_ref") or "")!=verification_ref:
            raise ValueError("promotion references do not match verified lifecycle evidence")
        result=self.model_scout.promote(spec.model_id,review_ref=review_ref,verification_ref=verification_ref)
        state.update({"reviewed":True,"verified":True,"routing_enabled":True,
                      "review_ref":review_ref,"verification_ref":verification_ref})
        self._advance_stage_state(state,"ROUTING_ENABLED")
        self._save_lifecycle(lifecycle)
        return {"model":spec.model_id,"scout":result,"lifecycle":dict(state)}

    def mobile_plan(self):
        return {
            "model":self.SPECS["spark-x2.5-1.7b"].model_id,
            "role":"LOCAL_MOBILE_REASONER",
            "packaged_in_apk":False,
            "automatic_download":False,
            "selected_runtime_candidate":"llama.cpp-android",
            "runtime_verified_in_krishna_mobile":False,
            "alternative_runtime_candidates":["native-ndk-jni"],
            "litert_status":"UNVERIFIED_UPSTREAM_DO_NOT_CLAIM",
            "model_manager":{
                "location":"app-private approved KRISHNA model storage",
                "checksum_required":True,"version_required":True,"storage_preflight":True,
                "resumable_download_required":True,"corruption_recovery_required":True,
            },
            "offline_behavior":{
                "when_runtime_absent":"QUEUE_FOR_PC",
                "when_runtime_verified":"local reasoning for intent/routing/structured HAWKEYE metadata only",
                "raw_hawkeye_media_cloud_escalation":False,
            },
        }

    def status(self):
        lifecycle=self._load_lifecycle()
        return {
            "component":"KRISHNA Spark-X2.5 Candidate Manager",
            "version":self.VERSION,
            "official_source":self.OFFICIAL_REPO,
            "license":self.LICENSE,
            "models":{k:{**self.candidate_metadata(k),"lifecycle":lifecycle.get("models",{}).get(k,{})} for k in self.SPECS},
            "ollama":self.ollama_status(),
            "mobile":self.mobile_plan(),
            "promotion_policy":"DISCOVERED -> DOWNLOADED -> BENCHMARKED -> CANDIDATE -> REVIEWED -> VERIFIED -> ROUTING_ENABLED",
            "vendor_claims_are_not_benchmark_evidence":True,
        }
