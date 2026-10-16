import pytest

from krishna_core.brahmagyan_learning_bridge import BrahmagyanLearningBridge
from krishna_core.external_learning_ledger import ExternalLearningLedger


class FakeBrahmagyan:
    def __init__(self):
        self.missions = []
        self.questions = []
    def create_mission(self, **kwargs):
        self.missions.append(kwargs)
        return {"mission_id": "m1"}
    def perspective_plan(self, mission_id, limit):
        return [{"rishi_id": "gautama"}, {"rishi_id": "veda-vyasa"}]
    def shishya_plan(self, mission_id, count, specialties):
        return {"count": count, "specialties": specialties}
    def add_questions(self, mission_id, questions):
        self.questions.extend(questions)


def test_approved_external_lesson_creates_l0_research_only(tmp_path):
    ledger = ExternalLearningLedger(tmp_path / "learning.sqlite3")
    fake = FakeBrahmagyan()
    bridge = BrahmagyanLearningBridge(fake, ledger)
    item = bridge.capture_source(source_url="https://github.com/example/repo",
        source_revision="commit-123", license_id="MIT",
        summary="Reproducible scheduling", evidence="Pinned source review")
    with pytest.raises(PermissionError):
        bridge.propose_research(item["id"])
    ledger.review(item["id"], reviewer="owner", tests_passed=True,
                  provenance_verified=True, license_verified=True, approved=True)
    result = bridge.propose_research(item["id"], shishya_count=99)
    assert result["authority"] == "BRAHMAGYAN"
    assert result["maturity"] == "L0"
    assert result["experiment_execution"] == "not_started"
    assert result["gyan_promotion"] == "not_requested"
    assert result["shishya_plan"]["count"] == 8
    assert fake.missions[0]["knowledge_track"] == "engineering"
    assert fake.questions
    ledger.close()
