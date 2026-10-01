from krishna_core.memory import MemoryStore
from krishna_core.gyan_bhandar import GyanBhandarAgent

def test_persistent_invalidation_propagates_and_verified_recall_excludes_descendants(tmp_path):
    m=MemoryStore(str(tmp_path/"m.db"))
    root=m.learn("P","source","paper A",[],.9,"paper",True,provenance={})
    claim=m.learn("P","claim","claim B",[],.9,"brahmagyan",True,provenance={"derived_from":[root["fingerprint"]]})
    gyan=m.learn("P","synthesis","gyan C",[],.9,"brahma",True,provenance={"derived_from":[claim["fingerprint"]]})
    other=m.learn("P","other","independent D",[],.9,"paper",True,provenance={})
    out=m.invalidate_learning_tree("P",root["fingerprint"],"source retracted","doi:test")
    assert set(out["affected"])=={root["fingerprint"],claim["fingerprint"],gyan["fingerprint"]}
    verified={x["fingerprint"] for x in m.learnings("P",verified_only=True)}
    assert other["fingerprint"] in verified
    assert root["fingerprint"] not in verified and claim["fingerprint"] not in verified and gyan["fingerprint"] not in verified
    rows={x["fingerprint"]:x for x in m.learnings("P",include_superseded=True)}
    assert rows[gyan["fingerprint"]]["status"]=="needs_review"
    assert rows[gyan["fingerprint"]]["provenance"]["invalidated_by"]==root["fingerprint"]
    assert any(x["action"]=="gyan_invalidation" for x in m.recent_audit())

def test_invalidation_is_safe_when_repeated(tmp_path):
    m=MemoryStore(str(tmp_path/"m.db"))
    root=m.learn("P","s","x",[],.9,"paper",True,provenance={})
    a=m.invalidate_learning_tree("P",root["fingerprint"],"stale")
    b=m.invalidate_learning_tree("P",root["fingerprint"],"stale")
    assert a["affected"]==b["affected"]==[root["fingerprint"]]
