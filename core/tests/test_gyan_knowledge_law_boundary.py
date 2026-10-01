import pytest
from krishna_core.gyan_bhandar import GyanBhandarAgent

class Memory:
    def __init__(self): self.saved=[];self.audits=[]
    def learn(self,*args): self.saved.append(args); return {"fingerprint":"ok","status":"verified" if args[6] else "candidate"}
    def audit(self,*args): self.audits.append(args)

def test_direct_verified_write_cannot_bypass_independence_law():
    m=Memory();g=GyanBhandarAgent.__new__(GyanBhandarAgent);g.memory=m
    evidence=[{"source_family":"same-origin","reality_level":"reported"}]
    with pytest.raises(ValueError,match="R7"):
        g.store("P","T","L",evidence,.9,"research",True)
    assert m.saved==[]

def test_retracted_evidence_cannot_be_stored_as_verified():
    m=Memory();g=GyanBhandarAgent.__new__(GyanBhandarAgent);g.memory=m
    evidence=[{"source_family":"a","reality_level":"reported","retracted":True},
              {"source_family":"b","reality_level":"reported"}]
    with pytest.raises(ValueError,match="R8"):
        g.store("P","T","L",evidence,.9,"research",True)

def test_candidate_write_remains_allowed_for_unverified_learning():
    m=Memory();g=GyanBhandarAgent.__new__(GyanBhandarAgent);g.memory=m
    r=g.store("P","T","hypothesis",[{"source_family":"a","reality_level":"reported"}],.4,"research",False)
    assert r["status"]=="candidate" and len(m.saved)==1

def test_valid_independent_verified_write_records_gate():
    m=Memory();g=GyanBhandarAgent.__new__(GyanBhandarAgent);g.memory=m
    evidence=[{"source_family":"a","reality_level":"reported"},
              {"source_family":"b","reality_level":"reported"}]
    r=g.store("P","T","L",evidence,.9,"research",True,provenance={"context":"test"})
    assert r["status"]=="verified"
    assert m.saved[0][9]["knowledge_law_gate"]["allowed"] is True
