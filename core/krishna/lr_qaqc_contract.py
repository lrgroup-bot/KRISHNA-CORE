from __future__ import annotations
from typing import Any
LR_QAQC_CONTRACT_VERSION="1.0.0"
VALID_EVENTS=frozenset({"ASSIGNMENT","VERDICT","OUTCOME","REPAIR","LEARNING"})
def validate_lr_qaqc_event(x:dict[str,Any])->dict[str,Any]:
    required=("eventId","eventType","assignmentId","companyId","domain","stage","artifactId","artifactVersion","payload")
    errors=[f"missing:{k}" for k in required if x.get(k) in (None,"")]
    if x.get("schema")!="lr.qaqc.event.v1": errors.append("schema")
    if x.get("contractVersion")!=LR_QAQC_CONTRACT_VERSION: errors.append("contractVersion")
    if x.get("eventType") not in VALID_EVENTS: errors.append("eventType")
    if int(x.get("artifactVersion") or 0)<1: errors.append("artifactVersion")
    if x.get("authority",{}).get("reportsTo")!="KRISHNA" or x.get("authority",{}).get("directHumanContact") is not False: errors.append("authority")
    if x.get("truth",{}).get("simulationIsHypothesis") is not True: errors.append("truth")
    return {"valid":not errors,"errors":errors,"route":"KRISHNA" if not errors else "REJECT_CONTRACT"}
