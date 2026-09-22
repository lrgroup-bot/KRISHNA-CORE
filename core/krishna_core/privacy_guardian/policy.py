from __future__ import annotations

from .models import PrivacyPolicyLevel, PrivacyRiskClass


_POLICY_REQUIRED={
    PrivacyPolicyLevel.STANDARD:{
        "browser":["browser.gpc","browser.webgl","browser.canvas","browser.permissions","browser.storage"],
        "web":["web.https","web.csp","web.referrer_policy"],
        "mobile":["mobile.trackers.static","mobile.cleartext_urls","mobile.permissions"],
        "network":["network.public_ip","network.http_headers"],
    },
    PrivacyPolicyLevel.STRICT:{
        "browser":["browser.gpc","browser.webgl","browser.canvas","browser.audio_context","browser.permissions","browser.storage","browser.webrtc","browser.third_party_requests"],
        "web":["web.https","web.hsts","web.csp","web.referrer_policy","web.permissions_policy","web.x_content_type_options","web.frame_protection","web.cookies"],
        "mobile":["mobile.trackers.static","mobile.cleartext_urls","mobile.permissions"],
        "network":["network.public_ip","network.tls_fingerprint","network.http_headers"],
    },
    PrivacyPolicyLevel.RESEARCH:{},
    PrivacyPolicyLevel.MOBILE_RELEASE:{
        "mobile":["mobile.trackers.static","mobile.cleartext_urls","mobile.permissions"],
    },
    PrivacyPolicyLevel.WEB_RELEASE:{
        "web":["web.https","web.hsts","web.csp","web.referrer_policy","web.permissions_policy","web.x_content_type_options","web.frame_protection","web.cookies"],
    },
}


def required_tests(policy: PrivacyPolicyLevel|str,target_type: str) -> list[str]:
    p=policy if isinstance(policy,PrivacyPolicyLevel) else PrivacyPolicyLevel(str(policy))
    return list((_POLICY_REQUIRED.get(p) or {}).get(str(target_type),[]))


def evaluate_release_gate(report: dict, policy: PrivacyPolicyLevel|str) -> dict:
    p=policy if isinstance(policy,PrivacyPolicyLevel) else PrivacyPolicyLevel(str(policy))
    target=str(report.get("target_type") or "")
    findings={str(x.get("test")):x for x in (report.get("findings") or []) if isinstance(x,dict)}
    required=required_tests(p,target)
    missing=[x for x in required if x not in findings]
    blocking=[]
    for name in required:
        row=findings.get(name) or {}
        risk=str(row.get("risk_class") or "")
        state=str(row.get("state") or "")
        if risk in {PrivacyRiskClass.PRIVACY_REGRESSION.value,PrivacyRiskClass.CONFIGURATION_INCONSISTENCY.value}:
            blocking.append({"test":name,"reason":risk})
        if p in {PrivacyPolicyLevel.MOBILE_RELEASE,PrivacyPolicyLevel.WEB_RELEASE,PrivacyPolicyLevel.STRICT} and state in {"failed"}:
            blocking.append({"test":name,"reason":"required_test_failed"})
    passed=not missing and not blocking
    return {
        "policy":p.value,
        "target_type":target,
        "required_tests":required,
        "missing_required":missing,
        "blocking_findings":blocking,
        "passed":passed,
        "informational_findings_do_not_block":True,
    }
