from datetime import datetime
from zoneinfo import ZoneInfo

from krishna_core.rishi_council import RishiCouncil
from krishna_core.system_design_curriculum import CURRICULUM, SystemDesignCurriculum


def test_curriculum_has_both_alex_xu_volumes_and_synthesis(tmp_path):
    c = SystemDesignCurriculum(tmp_path)
    schedule = c.schedule()
    assert len(CURRICULUM) == 30
    assert {x["volume"] for x in schedule["modules"]} == {0, 1, 2}
    assert schedule["modules"][0]["id"] == "v1-01-scale"
    assert schedule["modules"][14]["id"] == "v1-15-drive"
    assert schedule["modules"][15]["id"] == "v2-01-proximity"
    assert schedule["modules"][-1]["id"] == "synthesis-02"


def test_curriculum_uses_official_public_sources_not_pdf_copy(tmp_path):
    c = SystemDesignCurriculum(tmp_path)
    policy = c.source_policy()
    urls = " ".join(x["url"] for x in policy["official_index"]).lower()
    assert "alex-xu-system/bytebytego" in urls
    assert "bytebytegohq/system-design-101" in urls
    assert ".pdf" not in urls
    assert any("unauthorized full-book" in rule for rule in policy["rules"])


def test_next_assignment_starts_with_capacity_scale_module(tmp_path):
    c = SystemDesignCurriculum(tmp_path)
    now = datetime(2026, 10, 1, 3, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    assignment = c.next_assignment(now)
    assert assignment["id"] == "v1-01-scale"
    assert assignment["lead_rishi"] == "bharadvaja"
    assert "gautama" in assignment["team"]
    assert "veda-vyasa" in assignment["team"]


def test_verified_result_moves_to_next_due_module(tmp_path):
    c = SystemDesignCurriculum(tmp_path)
    now = datetime(2026, 10, 2, 3, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    c.record_result("v1-01-scale", mission_id="m1", run_id="r1",
                    scorecard={"cross_checked_claims": 2, "source_count": 5})
    assignment = c.next_assignment(now)
    assert assignment["id"] == "v1-02-estimation"


def test_weak_result_retries_same_module(tmp_path):
    c = SystemDesignCurriculum(tmp_path)
    now = datetime(2026, 10, 2, 15, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    c.record_result("v1-01-scale", scorecard={"cross_checked_claims": 0, "source_count": 1})
    assignment = c.next_assignment(now)
    assert assignment["id"] == "v1-01-scale"
    assert assignment["attempt"] == 2


def test_rishi_council_routes_system_design_specialists():
    council = RishiCouncil()
    ids = [x["id"] for x in council.select(
        "distributed systems rate limiting message queues consistent hashing system design", 6
    )]
    assert "jamadagni" in ids
    assert "pingala" in ids
    assert "bharadvaja" in ids
    assert "gautama" in ids
    assert "veda-vyasa" in ids
