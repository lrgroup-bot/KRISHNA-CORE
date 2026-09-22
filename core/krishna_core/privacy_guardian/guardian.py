from __future__ import annotations

from pathlib import Path
import json
import os
import uuid

from .browser import compare_browser_reports
from .mobile import MobSFAdapter, basic_apk_privacy_audit
from .models import (
    PrivacyAuditReport,
    PrivacyFinding,
    PrivacyPolicyLevel,
    PrivacyProfile,
    PrivacyRetentionClass,
    PrivacyRiskClass,
    utc_now,
)
from .network import NetworkPrivacyProbeClient
from .policy import evaluate_release_gate
from .regression import compare_reports
from .store import PrivacyEvidenceStore
from .tracking import LocalTrackerProvider, TrackerBehaviorLearner, clean_tracking_url
from .web_security import audit_web_endpoint


def _profile(value) -> PrivacyProfile:
    if isinstance(value,PrivacyProfile):
        return value
    raw=str(value or "BASELINE").strip().upper()
    try:return PrivacyProfile(raw)
    except ValueError:return PrivacyProfile.BASELINE


def _policy(value) -> PrivacyPolicyLevel:
    if isinstance(value,PrivacyPolicyLevel):
        return value
    raw=str(value or "STANDARD").strip().upper()
    try:return PrivacyPolicyLevel(raw)
    except ValueError:return PrivacyPolicyLevel.STANDARD


def _finding(row: dict) -> PrivacyFinding:
    risk=str(row.get("risk_class") or PrivacyRiskClass.INCONCLUSIVE.value)
    try:risk_enum=PrivacyRiskClass(risk)
    except ValueError:risk_enum=PrivacyRiskClass.INCONCLUSIVE
    return PrivacyFinding(
        test=str(row.get("test") or "privacy.unknown"),
        state=str(row.get("state") or "inconclusive"),
        summary=str(row.get("summary") or ""),
        risk_class=risk_enum,
        evidence=dict(row.get("evidence") or {}),
        recommendation=str(row.get("recommendation") or ""),
        confidence=str(row.get("confidence") or "observed"),
        limitations=list(row.get("limitations") or []),
        source_methodology=str(row.get("source_methodology") or "KRISHNA native defensive privacy test"),
        test_case_version=str(row.get("test_case_version") or "1"),
        sensitive=bool(row.get("sensitive",False)),
    )


class PrivacyGuardian:
    """KABACH-owned privacy measurement, regression and release-gate capability."""

    VERSION="privacy-guardian-v1"

    def __init__(self,state_root: str|Path,*,memory=None,browser=None,event_bus=None,
                 gyan_bhandar=None,tracker_db: str|Path|None=None):
        self.state_root=Path(state_root)
        self.state_root.mkdir(parents=True,exist_ok=True)
        self.memory=memory
        self.browser=browser
        self.event_bus=event_bus
        self.gyan_bhandar=gyan_bhandar
        self.store=PrivacyEvidenceStore(self.state_root)
        self.network=NetworkPrivacyProbeClient()
        self.trackers=LocalTrackerProvider(tracker_db)
        self.tracker_learning=TrackerBehaviorLearner()
        self.mobsf=MobSFAdapter()
        self._metrics={
            "privacy_tests_total":0,
            "privacy_test_failures":0,
            "privacy_regressions":0,
            "fingerprint_stable_signals":0,
            "tracker_requests":0,
            "third_party_domains":0,
            "dns_probe_failures":0,
            "mobile_trackers_found":0,
            "web_security_header_failures":0,
        }

    def bind_runtime(self,*,browser=None,event_bus=None,gyan_bhandar=None):
        if browser is not None:self.browser=browser
        if event_bus is not None:self.event_bus=event_bus
        if gyan_bhandar is not None:self.gyan_bhandar=gyan_bhandar
        return self.status()

    def _emit(self,topic,payload):
        if not self.event_bus:return None
        try:return self.event_bus.publish(topic,payload,source="kabach-privacy-guardian")
        except Exception:return None

    def _remember_summary(self,report: dict):
        safe=self.store.sanitize(report)
        compact={
            "audit_id":report.get("audit_id"),
            "target_type":report.get("target_type"),
            "profile":report.get("profile"),
            "policy":report.get("policy"),
            "test_suite_version":report.get("test_suite_version"),
            "risk_counts":report.get("risk_counts") or {},
            "regression_count":len(report.get("regressions") or []),
            "status":report.get("status") or "completed",
            "evidence_refs":[{
                "sha256":x.get("sha256"),
                "encrypted":bool(x.get("encrypted")),
                "retention":x.get("retention"),
            } for x in (report.get("evidence_refs") or []) if isinstance(x,dict)],
        }
        compact=self.store.sanitize(compact)
        if self.memory:
            try:
                self.memory.remember(
                    "KRISHNA","kabach_privacy",
                    str(report.get("audit_id") or "privacy-audit"),
                    {"summary":compact},
                )
            except Exception:
                pass
        if self.gyan_bhandar:
            try:
                self.gyan_bhandar.store(
                    "KRISHNA",
                    "privacy/"+str(report.get("target_type") or "audit"),
                    json.dumps(compact,ensure_ascii=False,sort_keys=True),
                    evidence=list(compact.get("evidence_refs") or []),
                    confidence=1.0,
                    source="kabach-privacy-guardian",
                    verified=False,
                    memory_kind="evidence",
                    provenance={
                        "test_suite_version":report.get("test_suite_version"),
                        "audit_id":report.get("audit_id"),
                        "privacy_safe_summary":True,
                    },
                )
            except Exception:
                pass
        return safe

    def _finalize(self,report: PrivacyAuditReport,*,retention=PrivacyRetentionClass.REGRESSION_HISTORY) -> dict:
        data=report.as_dict()
        self._metrics["privacy_tests_total"]+=len(data.get("findings") or [])
        self._metrics["privacy_test_failures"]+=sum(1 for x in data.get("findings") or [] if str(x.get("state")).lower()=="failed")
        self._metrics["privacy_regressions"]+=len(data.get("regressions") or [])
        stored=self.store.append_history(data,retention)
        data["history_storage"]=stored
        data["verification_checks"]=report.verification_checks()
        data["risk_counts"]=report.counts
        self._remember_summary(data)
        self._emit("privacy.audit.completed",{
            "audit_id":report.audit_id,
            "target_type":report.target_type,
            "profile":report.profile.value,
            "policy":report.policy.value,
            "risk_counts":report.counts,
            "regressions":len(report.regressions),
        })
        return data

    def audit_browser(self,*,url: str="about:blank",profile="BASELINE",policy="STANDARD",
                      mission_id: str|None=None) -> dict:
        if not self.browser or not hasattr(self.browser,"privacy_probe"):
            report=PrivacyAuditReport(
                audit_id=audit_id,target_type="browser",profile=_profile(profile),
                policy=_policy(policy),created_at=utc_now(),test_suite_version=self.VERSION,
                findings=[PrivacyFinding(
                    test="browser.runtime",state="failed",
                    summary="Garudanetra browser privacy probe is unavailable.",
                    risk_class=PrivacyRiskClass.UNSUPPORTED,
                    recommendation="Enable the canonical Garudanetra/Playwright runtime before interpreting browser privacy.",
                )],
                metadata={"mission_id":mission_id},
            )
            return self._finalize(report)
        self._emit("privacy.audit.started",{"target_type":"browser","profile":str(profile)})
        audit_id=str(uuid.uuid4())
        raw=self.browser.privacy_probe(url=url,profile=_profile(profile).value)
        findings=[_finding(x) for x in raw.get("findings") or []]
        fingerprint=raw.get("fingerprint") or {}
        if fingerprint:
            evidence_ref=self.store.store_sensitive_evidence(
                audit_id,"browser-fingerprint",fingerprint,
                PrivacyRetentionClass.SECURITY_EVIDENCE,
            )
        else:evidence_ref=None
        third_party=((next((x for x in raw.get("findings") or [] if x.get("test")=="browser.third_party_requests"),{}) or {}).get("evidence") or {}).get("third_party_domains") or []
        self._metrics["third_party_domains"]+=len(third_party)
        self._metrics["tracker_requests"]+=int(raw.get("request_count") or 0)
        report=PrivacyAuditReport(
            audit_id=str(uuid.uuid4()),target_type="browser",profile=_profile(profile),
            policy=_policy(policy),created_at=utc_now(),test_suite_version=self.VERSION,
            target={"url":url},
            findings=findings,
            metadata={
                "mission_id":mission_id,
                "browser":raw.get("browser"),
                "surfaces":raw.get("surfaces"),
                "permissions":raw.get("permissions"),
                "storage":raw.get("storage"),
                "webrtc":raw.get("webrtc"),
                "temporary_profile":raw.get("temporary_profile"),
                "elapsed_ms":raw.get("elapsed_ms"),
                "fingerprint":fingerprint,
            },
            evidence_refs=[evidence_ref] if evidence_ref else [],
            limitations=["A single browser run cannot establish cross-session stability; compare compatible profiles/runs."],
        )
        return self._finalize(report)

    def audit_network(self,*,profile="BASELINE",policy="STANDARD",mission_id=None) -> dict:
        self._emit("privacy.audit.started",{"target_type":"network","profile":str(profile)})
        raw=self.network.audit()
        findings=[_finding(x) for x in raw.get("findings") or []]
        report=PrivacyAuditReport(
            audit_id=str(uuid.uuid4()),target_type="network",profile=_profile(profile),
            policy=_policy(policy),created_at=utc_now(),test_suite_version=self.VERSION,
            findings=findings,metadata={"mission_id":mission_id,"probe":self.network.status(),"errors":raw.get("errors") or {}},
            limitations=["DNS-resolver and client-TLS conclusions require a configured owner-controlled external observation service."],
        )
        return self._finalize(report)

    def audit_web(self,url: str,*,owned=True,profile="WEB_ENDPOINT",policy="WEB_RELEASE",mission_id=None) -> dict:
        self._emit("privacy.audit.started",{"target_type":"web","url":url})
        raw=audit_web_endpoint(url,owned=bool(owned))
        findings=[_finding(x) for x in raw.get("findings") or []]
        weak=sum(1 for x in findings if x.risk_class==PrivacyRiskClass.MODERATE_EXPOSURE)
        self._metrics["web_security_header_failures"]+=weak
        report=PrivacyAuditReport(
            audit_id=str(uuid.uuid4()),target_type="web",profile=_profile(profile),
            policy=_policy(policy),created_at=utc_now(),test_suite_version=self.VERSION,
            target={"url":url,"owned":bool(owned)},findings=findings,
            metadata={
                "mission_id":mission_id,"status":raw.get("status"),"final_url":raw.get("final_url"),
                "redirects":raw.get("redirects"),"headers_present":raw.get("headers_present"),
                "elapsed_ms":raw.get("elapsed_ms"),
            },
        )
        return self._finalize(report)

    def audit_mobile(self,apk_path: str,*,profile="KRISHNA_MOBILE",policy="MOBILE_RELEASE",mission_id=None) -> dict:
        self._emit("privacy.audit.started",{"target_type":"mobile","apk":str(apk_path)})
        raw=basic_apk_privacy_audit(apk_path)
        findings=[_finding(x) for x in raw.get("findings") or []]
        tracker_row=next((x for x in findings if x.test=="mobile.trackers.static"),None)
        if tracker_row:
            self._metrics["mobile_trackers_found"]+=len((tracker_row.evidence or {}).get("tracker_signatures") or [])
        report=PrivacyAuditReport(
            audit_id=str(uuid.uuid4()),target_type="mobile",profile=_profile(profile),
            policy=_policy(policy),created_at=utc_now(),test_suite_version=self.VERSION,
            target={"apk":str(apk_path),"apk_sha256":raw.get("apk_sha256")},
            findings=findings,
            metadata={
                "mission_id":mission_id,
                "mobsf":self.mobsf.status(),
                "full_gate_requires_mobsf":raw.get("mobsf_required_for_full_gate"),
                "full_gate_requires_dynamic_test":raw.get("dynamic_test_required_for_full_gate"),
            },
            limitations=["Static APK analysis is not equivalent to a real-device dynamic privacy test."],
        )
        return self._finalize(report)

    def classify_target(self,request: dict|None=None) -> str:
        data=dict(request or {})
        explicit=str(data.get("target_type") or data.get("target") or "").strip().lower()
        if explicit in {"browser","network","web","mobile","full"}:
            return explicit
        if str(data.get("apk_path") or "").strip():
            return "mobile"
        if str(data.get("url") or "").strip() and bool(data.get("web_endpoint",False)):
            return "web"
        return "full"

    def audit_full(self,*,url: str="about:blank",web_url: str|None=None,apk_path: str|None=None,
                   profile="BASELINE",policy="STANDARD",mission_id=None) -> dict:
        """Run every locally available privacy lane and keep unsupported external lanes honest."""
        self._emit("privacy.audit.started",{"target_type":"full","profile":str(profile)})
        reports={}
        errors={}
        try:
            reports["browser"]=self.audit_browser(
                url=url,profile=profile,policy=policy,mission_id=mission_id,
            )
        except Exception as exc:
            errors["browser"]=f"{type(exc).__name__}: {exc}"
        try:
            reports["network"]=self.audit_network(
                profile=profile,policy=policy,mission_id=mission_id,
            )
        except Exception as exc:
            errors["network"]=f"{type(exc).__name__}: {exc}"
        if web_url:
            try:
                reports["web"]=self.audit_web(
                    web_url,owned=True,profile="WEB_ENDPOINT",
                    policy="WEB_RELEASE",mission_id=mission_id,
                )
            except Exception as exc:
                errors["web"]=f"{type(exc).__name__}: {exc}"
        if apk_path:
            try:
                reports["mobile"]=self.audit_mobile(
                    apk_path,profile="KRISHNA_MOBILE",
                    policy="MOBILE_RELEASE",mission_id=mission_id,
                )
            except Exception as exc:
                errors["mobile"]=f"{type(exc).__name__}: {exc}"
        risk_counts={}
        regression_count=0
        for report in reports.values():
            regression_count+=len(report.get("regressions") or [])
            for key,value in (report.get("risk_counts") or {}).items():
                risk_counts[key]=risk_counts.get(key,0)+int(value or 0)
        out={
            "audit_id":str(uuid.uuid4()),
            "target_type":"full",
            "profile":_profile(profile).value,
            "policy":_policy(policy).value,
            "created_at":utc_now(),
            "test_suite_version":self.VERSION,
            "reports":reports,
            "errors":errors,
            "risk_counts":risk_counts,
            "regression_count":regression_count,
            "network_external_probe_configured":bool(self.network.status().get("configured")),
            "mobile_dynamic_verified":False if apk_path else None,
            "definition_of_done":{
                "browser_real_runtime":bool(reports.get("browser") and not errors.get("browser")),
                "web_real_endpoint":bool(web_url and reports.get("web") and not errors.get("web")),
                "network_external_runtime":bool(self.network.status().get("configured") and reports.get("network") and not errors.get("network")),
                "mobile_real_apk_static":bool(apk_path and reports.get("mobile") and not errors.get("mobile")),
                "mobile_dynamic_runtime":False,
            },
            "limitations":[
                "External IP/DNS/TLS observations require an explicitly configured KRISHNA-controlled probe.",
                "A full mobile release claim requires real-device dynamic testing in addition to static APK analysis.",
            ],
        }
        safe=self.store.sanitize(out)
        self.store.append_history(safe,PrivacyRetentionClass.REGRESSION_HISTORY)
        self._remember_summary(safe)
        self._emit("privacy.audit.completed",{
            "audit_id":out["audit_id"],"target_type":"full",
            "lanes":sorted(reports),"errors":sorted(errors),
            "regressions":regression_count,
        })
        return out

    def clean_url(self,url: str) -> dict:
        result=clean_tracking_url(url)
        self._emit("privacy.link.cleaned",{"changed":result.get("changed"),"removed_count":len(result.get("removed") or [])})
        return result

    def save_baseline(self,name: str,report: dict) -> dict:
        out=self.store.save_baseline(name,report)
        self._emit("privacy.baseline.saved",{"name":name,"sha256":out.get("sha256")})
        return out

    def compare_with_baseline(self,name: str,current: dict,*,mission_id=None,configuration_change=None) -> dict:
        base=self.store.baseline(name)
        if not base:
            raise KeyError(f"privacy baseline not found: {name}")
        result=compare_reports(base.get("report") or {},current or {},mission_id=mission_id,configuration_change=configuration_change)
        if result.get("regression_count"):
            alert={"kind":"privacy_regression","baseline":name,"count":result["regression_count"],"mission_id":mission_id}
            self._emit("privacy.regression.detected",alert)
            self._emit("SUDARSHAN_ALERT",alert)
        return result

    def compare_browser_profiles(self,a: dict,b: dict) -> dict:
        return compare_browser_reports(a,b)

    def release_gate(self,report: dict,policy="STANDARD") -> dict:
        gate=evaluate_release_gate(report,_policy(policy))
        gate["sudarshan_required"]=True
        gate["release_blocked"]=not gate["passed"]
        gate["policy_note"]="Informational findings do not block unless the configured policy makes the test mandatory."
        gate_event={
            "passed":gate["passed"],"policy":gate["policy"],"target_type":gate["target_type"],
            "blocking_count":len(gate["blocking_findings"])+len(gate["missing_required"]),
        }
        self._emit("privacy.release_gate",gate_event)
        if not gate["passed"]:
            self._emit("SUDARSHAN_ALERT",{"kind":"privacy_release_gate_failed",**gate_event})
        return gate

    def history(self,limit=50) -> list[dict]:
        return self.store.history(limit)

    def metrics(self) -> dict:
        return dict(self._metrics)

    def status(self) -> dict:
        return {
            "owner":"KABACH Privacy Guardian",
            "version":self.VERSION,
            "internal_only":True,
            "main_menu":False,
            "purpose":"defensive privacy measurement, regression testing, release gating and self-protection",
            "anti_detection":False,
            "browser_runtime_bound":bool(self.browser and hasattr(self.browser,"privacy_probe")),
            "network_probe":self.network.status(),
            "tracker_provider":self.trackers.status(),
            "mobsf":self.mobsf.status(),
            "storage_root":str(self.state_root),
            "storage_policy":"local-first; normalized history redacted; sensitive evidence persisted only with Windows DPAPI",
            "profiles":[x.value for x in PrivacyProfile],
            "policies":[x.value for x in PrivacyPolicyLevel],
            "retention_classes":[x.value for x in PrivacyRetentionClass],
            "risk_classes":[x.value for x in PrivacyRiskClass],
            "implemented":{
                "browser_exposure":True,
                "fingerprint_surface_inspector":True,
                "local_fingerprint_identifier":True,
                "webrtc_candidate_type_probe":True,
                "tracking_url_cleaner":True,
                "tracker_provider_abstraction":True,
                "tracker_behavior_evidence":True,
                "web_endpoint_headers":True,
                "privacy_regression_store":True,
                "release_gate":True,
                "mobile_static_apk_audit":True,
                "mobsf_adapter_boundary":True,
                "external_network_probe_client":True,
                "full_target_classifier":True,
            },
            "conditional_or_external":{
                "dns_leak_probe":"requires owner-controlled external DNS service",
                "public_ip_tls_ja4":"requires configured KRISHNA_PRIVACY_PROBE_URL",
                "mobsf_dynamic_mobile":"requires configured independent MobSF service",
                "openwpm_research":"external adapter only; not embedded",
                "exodus_amiunique":"methodology/provider boundary only; restrictive code not embedded",
            },
            "metrics":self.metrics(),
        }
