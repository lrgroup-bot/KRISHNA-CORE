import json
import pytest
from kuif.identity import Principal
from kuif.runtime import Runtime, RuntimeConfig

def test_runtime_denies_cross_project_and_audits(tmp_path):
    config = RuntimeConfig(str(tmp_path / "memory.db"), str(tmp_path / "audit.jsonl"))
    runtime = Runtime(config)
    principal = Principal("tester", frozenset({"krishna"}), frozenset({"read"}))
    with pytest.raises(PermissionError):
        runtime.search(principal, "kuber", "test")
    event = json.loads((tmp_path / "audit.jsonl").read_text().strip())
    assert event["allowed"] is False
    assert event["project"] == "kuber"

def test_runtime_scoped_memory(tmp_path):
    config = RuntimeConfig(str(tmp_path / "memory.db"), str(tmp_path / "audit.jsonl"))
    runtime = Runtime(config)
    runtime.memory.put("krishna", "d1", "hello world")
    principal = Principal("tester", frozenset({"krishna"}), frozenset({"read"}))
    assert runtime.search(principal, "krishna", "hello") == [("d1", "hello world")]

def test_runtime_analyze_mocked(tmp_path, monkeypatch):
    monkeypatch.setattr("kuif.runtime.generate", lambda model, prompt: "ok")
    runtime = Runtime(RuntimeConfig(str(tmp_path / "memory.db"), str(tmp_path / "audit.jsonl")))
    principal = Principal("tester", frozenset({"krishna"}), frozenset({"analyze"}))
    assert runtime.analyze(principal, "krishna", "hello") == "ok"
