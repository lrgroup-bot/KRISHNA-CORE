import json
import pytest
from kuif.audit import append_event

def test_append_audit(tmp_path):
    target = tmp_path / "events.jsonl"
    append_event(str(target), project="krishna", actor="user-1", action="read", allowed=True)
    event = json.loads(target.read_text().strip())
    assert event["project"] == "krishna"
    assert event["allowed"] is True
    assert "timestamp" in event

def test_missing_actor_rejected(tmp_path):
    with pytest.raises(ValueError):
        append_event(str(tmp_path / "events.jsonl"), project="krishna", actor="", action="read", allowed=True)
