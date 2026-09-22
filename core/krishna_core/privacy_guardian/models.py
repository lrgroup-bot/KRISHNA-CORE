from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PrivacyProfile(str, Enum):
    BASELINE="BASELINE"
    FRESH_PROFILE="FRESH_PROFILE"
    NORMAL_BROWSER="NORMAL_BROWSER"
    INCOGNITO="INCOGNITO"
    HARDENED_PROFILE="HARDENED_PROFILE"
    VPN_PROFILE="VPN_PROFILE"
    MOBILE_BROWSER="MOBILE_BROWSER"
    KRISHNA_MOBILE="KRISHNA_MOBILE"
    WEB_ENDPOINT="WEB_ENDPOINT"


class PrivacyPolicyLevel(str, Enum):
    STANDARD="STANDARD"
    STRICT="STRICT"
    RESEARCH="RESEARCH"
    MOBILE_RELEASE="MOBILE_RELEASE"
    WEB_RELEASE="WEB_RELEASE"


class PrivacyRiskClass(str, Enum):
    LOW_EXPOSURE="LOW EXPOSURE"
    MODERATE_EXPOSURE="MODERATE EXPOSURE"
    HIGH_LINKABILITY="HIGH LINKABILITY"
    CONFIGURATION_INCONSISTENCY="CONFIGURATION INCONSISTENCY"
    PRIVACY_REGRESSION="PRIVACY REGRESSION"
    UNSUPPORTED="UNSUPPORTED"
    INCONCLUSIVE="INCONCLUSIVE"


class PrivacyRetentionClass(str, Enum):
    EPHEMERAL="EPHEMERAL"
    BASELINE="BASELINE"
    REGRESSION_HISTORY="REGRESSION_HISTORY"
    SECURITY_EVIDENCE="SECURITY_EVIDENCE"


@dataclass(slots=True)
class PrivacyFinding:
    test: str
    state: str
    summary: str
    risk_class: PrivacyRiskClass=PrivacyRiskClass.INCONCLUSIVE
    evidence: dict[str,Any]=field(default_factory=dict)
    recommendation: str=""
    confidence: str="observed"
    limitations: list[str]=field(default_factory=list)
    source_methodology: str="KRISHNA native defensive privacy test"
    test_case_version: str="1"
    sensitive: bool=False

    def as_dict(self) -> dict:
        row=asdict(self)
        row["risk_class"]=self.risk_class.value
        return row


@dataclass(slots=True)
class PrivacyAuditReport:
    audit_id: str
    target_type: str
    profile: PrivacyProfile
    policy: PrivacyPolicyLevel
    created_at: str
    test_suite_version: str
    target: dict[str,Any]=field(default_factory=dict)
    findings: list[PrivacyFinding]=field(default_factory=list)
    metadata: dict[str,Any]=field(default_factory=dict)
    evidence_refs: list[dict[str,Any]]=field(default_factory=list)
    regressions: list[dict[str,Any]]=field(default_factory=list)
    status: str="completed"
    limitations: list[str]=field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "audit_id":self.audit_id,
            "target_type":self.target_type,
            "profile":self.profile.value,
            "policy":self.policy.value,
            "created_at":self.created_at,
            "test_suite_version":self.test_suite_version,
            "target":dict(self.target),
            "findings":[x.as_dict() for x in self.findings],
            "metadata":dict(self.metadata),
            "evidence_refs":[dict(x) for x in self.evidence_refs],
            "regressions":[dict(x) for x in self.regressions],
            "status":self.status,
            "limitations":list(self.limitations),
        }

    @property
    def counts(self) -> dict[str,int]:
        out={}
        for item in self.findings:
            key=item.risk_class.value
            out[key]=out.get(key,0)+1
        return out

    def verification_checks(self) -> list[dict]:
        checks=[]
        for item in self.findings:
            fail=item.risk_class in {
                PrivacyRiskClass.PRIVACY_REGRESSION,
                PrivacyRiskClass.CONFIGURATION_INCONSISTENCY,
            }
            checks.append({
                "name":"privacy:"+item.test,
                "status":"FAIL" if fail else "PASS",
                "passed":not fail,
                "detail":item.summary,
            })
        if not checks:
            checks.append({
                "name":"privacy:audit-result",
                "status":"FAIL",
                "passed":False,
                "detail":"audit produced no findings",
            })
        return checks
