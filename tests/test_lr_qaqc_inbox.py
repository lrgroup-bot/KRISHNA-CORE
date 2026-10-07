from core.krishna.lr_qaqc_inbox import LRQAQCInbox
def e(eid,v):
    return {"schema":"lr.qaqc.event.v1","contractVersion":"1.0.0","eventId":eid,"eventType":"VERDICT","assignmentId":"a","companyId":"lr-commerce","domain":"commerce","stage":"listing","artifactId":"sku","artifactVersion":v,"payload":{},"authority":{"reportsTo":"KRISHNA","directHumanContact":False},"truth":{"simulationIsHypothesis":True}}
def test_inbox_is_idempotent_and_version_ordered():
    x=LRQAQCInbox();assert x.accept(e("e1",1))["accepted"];assert x.accept(e("e1",1))["reason"]=="DUPLICATE_EVENT";assert x.accept(e("e3",3))["reason"]=="VERSION_GAP";assert x.accept(e("e2",2))["accepted"];assert x.accept(e("old",1))["reason"]=="STALE_ARTIFACT_VERSION"
