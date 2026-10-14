import pytest
from krishna_core.mission_engine import MissionEngine

def test_mission_cannot_skip_verification(tmp_path):
    m=MissionEngine(str(tmp_path/"m.db"))
    x=m.create("test")
    with pytest.raises(ValueError,match="VERIFYING"):
        m.transition(x["mission_id"],"COMPLETED",verification_status="passed")

def test_mission_cannot_complete_with_failed_or_pending_verification(tmp_path):
    m=MissionEngine(str(tmp_path/"m.db"))
    x=m.create("test")
    m.transition(x["mission_id"],"RUNNING")
    m.transition(x["mission_id"],"VERIFYING")
    with pytest.raises(ValueError,match="passed verification"):
        m.transition(x["mission_id"],"COMPLETED")
    with pytest.raises(ValueError,match="passed verification"):
        m.transition(x["mission_id"],"COMPLETED",verification_status="failed")

def test_verified_mission_can_complete(tmp_path):
    m=MissionEngine(str(tmp_path/"m.db"))
    x=m.create("test")
    m.transition(x["mission_id"],"RUNNING")
    m.transition(x["mission_id"],"VERIFYING")
    done=m.transition(x["mission_id"],"COMPLETED",verification_status="passed",progress=1)
    assert done["status"]=="COMPLETED" and done["verification_status"]=="passed"
