from core.krishna.lr_qaqc_contract import validate_lr_qaqc_event
def test_krishna_accepts_canonical_qaqc_event():
    x={"schema":"lr.qaqc.event.v1","contractVersion":"1.0.0","eventId":"e1","eventType":"VERDICT","assignmentId":"a1","companyId":"lr-commerce","domain":"commerce","stage":"listing","artifactId":"sku1","artifactVersion":1,"payload":{},"authority":{"reportsTo":"KRISHNA","directHumanContact":False},"truth":{"simulationIsHypothesis":True}}
    assert validate_lr_qaqc_event(x)=={"valid":True,"errors":[],"route":"KRISHNA"}
def test_krishna_rejects_contract_drift():
    x={"schema":"wrong","contractVersion":"1.0.0","eventId":"e1","eventType":"VERDICT","assignmentId":"a1","companyId":"lr-commerce","domain":"commerce","stage":"listing","artifactId":"sku1","artifactVersion":1,"payload":{},"authority":{"reportsTo":"KRISHNA","directHumanContact":False},"truth":{"simulationIsHypothesis":True}}
    assert validate_lr_qaqc_event(x)["route"]=="REJECT_CONTRACT"
