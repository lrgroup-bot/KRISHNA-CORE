import tempfile
from pathlib import Path
from krishna_core.universal_learning import UniversalLearningRuntime

def runtime():
    return UniversalLearningRuntime(Path(tempfile.mkdtemp()))

def test_natural_learning_has_no_fixed_command():
    r=runtime()
    a=r.infer_intent("Krishna listen to this and tell me what noise it is",["audio"])
    b=r.infer_intent("Please study what I am watching",["video","audio"])
    assert a["intent"]=="investigate"
    assert b["intent"]=="learn"

def test_unknown_escalates_and_routes_sound():
    r=runtime()
    x=r.ingest(utterance="what is that sound",source_type="mobile",
               modalities=["audio"],subject="unknown sound",confidence=.31)
    assert x["escalate"] is True
    assert x["rishi"]=="patanjali"
    assert x["unknown_resolution"]["status"]=="research_required"

def test_confident_observation_does_not_force_research():
    r=runtime()
    x=r.ingest(utterance="what is this",source_type="camera",modalities=["image"],
               subject="plant",confidence=.92,analysis="candidate plant",
               evidence_state="OBSERVED")
    assert x["escalate"] is False

def test_sound_taxonomy_keeps_unknown_safe():
    r=runtime()
    x=r.classify_sound_request("what is this noise")
    assert x["candidate_classes"]==["unknown"]
    assert "UNKNOWN" in x["rule"]
