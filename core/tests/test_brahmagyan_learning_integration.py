"""Integration checks against the *real* BRAHMAGYAN runtime, not a mock."""
import pytest
from krishna_core.brahmagyan import BrahmagyanRuntime
from krishna_core.brahmagyan_learning_bridge import BrahmagyanLearningBridge
from krishna_core.external_learning_ledger import ExternalLearningLedger


def test_real_brahmagyan_bridge_preserves_maturity_and_persists(tmp_path):
    root = tmp_path / "brahmagyan"
    brain = BrahmagyanRuntime(root, gyan=None, memory=None)
    ledger = ExternalLearningLedger(tmp_path / "external.sqlite3")
    bridge = BrahmagyanLearningBridge(brain, ledger)
    lesson = bridge.capture_source(
        source_url="https://github.com/example/research",
        source_revision="sha256-abc", license_id="MIT",
        summary="Reproducible event scheduling",
        evidence="Source revision and test protocol pending independent verification")
    with pytest.raises(PermissionError):
        bridge.propose_research(lesson["id"])
    assert brain.missions() == []
    ledger.review(lesson["id"], reviewer="owner", tests_passed=True,
                  provenance_verified=True, license_verified=True, approved=True)
    plan = bridge.propose_research(lesson["id"], shishya_count=3)
    mission_id = plan["mission_id"]
    assert plan["maturity"] == "L0"
    assert plan["gyan_promotion"] == "not_requested"
    assert plan["experiment_execution"] == "not_started"
    assert len(plan["perspectives"]) >= 3
    assert brain.mission(mission_id)["knowledge_track"] == "engineering"
    assert brain.mission(mission_id)["maturity"] == "L0"
    assert len(brain.mission(mission_id)["research_questions"]) >= 3
    restarted = BrahmagyanRuntime(root, gyan=None, memory=None)
    assert restarted.mission(mission_id)["maturity"] == "L0"
    assert restarted.mission(mission_id)["shishya_batches"]
    assert restarted.state["claims"] == {}
    ledger.close()
