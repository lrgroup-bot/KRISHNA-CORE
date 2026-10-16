import pytest

from krishna_core.agent_live_projection import AgentLiveProjection, project_agent_event


def event(**overrides):
    row = {"agent_id": "sudarshan", "state": "working", "sequence": 1,
           "timestamp": 100.0, "task_id": "project-1", "progress": 0.5}
    row.update(overrides)
    return row


def test_live_event_projects_real_state_without_claiming_success():
    result = project_agent_event(event(), now=105)
    assert result["display_status"] == "WORKING"
    assert result["progress"] == 0.5
    assert result["verified_completion"] is False


def test_stale_event_is_not_presented_as_live():
    result = project_agent_event(event(verified_completion=True), now=140)
    assert result["stale"] is True
    assert result["state"] == "unknown"
    assert result["progress"] is None
    assert result["verified_completion"] is False


def test_sequence_guard_rejects_replay_and_out_of_order_events():
    projection = AgentLiveProjection()
    projection.ingest(event(), now=100)
    with pytest.raises(ValueError):
        projection.ingest(event(), now=101)
    with pytest.raises(ValueError):
        projection.ingest(event(sequence=0), now=101)
    assert projection.ingest(event(sequence=2, state="blocked"), now=101)["state"] == "blocked"
    assert projection.snapshot(now=140)[0]["display_status"] == "STALE"


@pytest.mark.parametrize("bad", [
    {"state": "success"}, {"agent_id": ""}, {"sequence": -1},
    {"sequence": True}, {"progress": 1.2}, {"timestamp": float("nan")},
    {"timestamp": 110.0}, {"verified_completion": "yes"},
])
def test_bad_events_rejected_or_do_not_fabricate_success(bad):
    if "verified_completion" in bad:
        assert project_agent_event(event(**bad), now=100)["verified_completion"] is False
    else:
        with pytest.raises(ValueError):
            project_agent_event(event(**bad), now=100)
