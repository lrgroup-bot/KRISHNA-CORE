from __future__ import annotations

from .models import PrivacyRiskClass, utc_now


def _index_findings(report: dict) -> dict:
    return {
        str(x.get("test")):x for x in (report.get("findings") or [])
        if isinstance(x,dict) and x.get("test")
    }


def compare_reports(previous: dict, current: dict, *, mission_id: str|None=None,
                    configuration_change: str|None=None) -> dict:
    prev=_index_findings(previous or {})
    curr=_index_findings(current or {})
    regressions=[];changes=[]
    keys=sorted(set(prev)|set(curr))
    for key in keys:
        a=prev.get(key);b=curr.get(key)
        if a==b:
            continue
        row={
            "test":key,
            "previous_value":a,
            "current_value":b,
            "timestamp":utc_now(),
            "mission_id":mission_id,
            "configuration_change":configuration_change,
            "supporting_evidence":{
                "previous_audit_id":(previous or {}).get("audit_id"),
                "current_audit_id":(current or {}).get("audit_id"),
                "test_suite_version":(current or {}).get("test_suite_version"),
                "profile":(current or {}).get("profile"),
            },
        }
        changes.append(row)
        old_risk=str((a or {}).get("risk_class") or "")
        new_risk=str((b or {}).get("risk_class") or "")
        worsened=new_risk in {
            PrivacyRiskClass.PRIVACY_REGRESSION.value,
            PrivacyRiskClass.CONFIGURATION_INCONSISTENCY.value,
            PrivacyRiskClass.HIGH_LINKABILITY.value,
            PrivacyRiskClass.MODERATE_EXPOSURE.value,
        } and old_risk not in {
            PrivacyRiskClass.PRIVACY_REGRESSION.value,
            PrivacyRiskClass.CONFIGURATION_INCONSISTENCY.value,
            PrivacyRiskClass.HIGH_LINKABILITY.value,
            PrivacyRiskClass.MODERATE_EXPOSURE.value,
        }
        if worsened:
            regressions.append({**row,"classification":PrivacyRiskClass.PRIVACY_REGRESSION.value})
    compatible=(previous or {}).get("test_suite_version")==(current or {}).get("test_suite_version")
    return {
        "compatible_methodology":bool(compatible),
        "change_count":len(changes),
        "regression_count":len(regressions),
        "changes":changes,
        "regressions":regressions,
        "note":"Historical results are directly comparable only when test-suite versions are compatible." if not compatible else "",
    }
