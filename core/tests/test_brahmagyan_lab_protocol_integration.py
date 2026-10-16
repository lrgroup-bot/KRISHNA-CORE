"""BRAHMAGYAN must reuse LAB BOT and never mark proposed experiments executed."""
import pytest
from krishna_core.brahmagyan import BrahmagyanRuntime

class AuditMemory:
    def audit(self, *args, **kwargs):
        return None
from krishna_core.brahmagyan_learning_bridge import BrahmagyanLearningBridge
from krishna_core.external_learning_ledger import ExternalLearningLedger
from krishna_core.lab_bot import LabBot


def test_existing_lab_bot_receives_proposal_only(tmp_path):
    brain=BrahmagyanRuntime(tmp_path/"brain", gyan=None, memory=AuditMemory())
    ledger=ExternalLearningLedger(tmp_path/"lessons.sqlite3")
    bridge=BrahmagyanLearningBridge(brain, ledger)
    lab=LabBot(tmp_path/"lab")
    mission=brain.create_mission("KRISHNA","Software scheduling reproducibility",
                                knowledge_track="engineering")
    with pytest.raises(ValueError):
        bridge.propose_lab_protocol(mission["mission_id"], lab, hypothesis="A", objective="B",
                                    controls=[], measurements=["latency"], success_criteria=["stable"])
    result=bridge.propose_lab_protocol(mission["mission_id"], lab,
        hypothesis="Bounded scheduling reduces tail latency",
        objective="Compare scheduler against a baseline",
        controls=["same workload"], measurements=["p95 latency"],
        success_criteria=["lower p95 in repeated tests"])
    experiment_id=result["experiment_id"]
    stored=lab.get(experiment_id)
    assert stored["status"] == "PLANNED"
    assert stored["mode"] == "simulation"
    assert f"brahmagyan:mission:{mission['mission_id']}" in stored["source_refs"]
    assert brain.mission(mission["mission_id"])["maturity"] == "L0"
    assert brain.state["claims"] == {}
    ledger.close()

    feedback=bridge.inspect_lab_feedback(mission["mission_id"],lab)
    assert feedback["read_only"] is True
    assert feedback["claims_created"] == 0
    assert feedback["promotion_requested"] is False
    assert len(feedback["experiments"]) == 1
    assert feedback["experiments"][0]["experiment_id"] == experiment_id
    assert feedback["experiments"][0]["evidence_count"] == 0
